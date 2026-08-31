/*
 * This is driver implementation for the RTL837x flash controller
 * This code is in the Public Domain
 */

#include <stdint.h>
#include "rtl837x_common.h"
#include "rtl837x_sfr.h"

__xdata uint8_t dio_enabled;
__xdata struct flash_region_t flash_region;

__xdata uint32_t flash_size;
__xdata uint8_t flash_capacity_code;

// For the flash commands, see e.g. Windbond W25Q32JV datasheet
#define CMD_WRITE_STATUS	0x01
#define CMD_PAGE_PROGRAM	0x02
// Don't use command `READ 0x03`, because on many device this command can't run at maximum SPI-clock speed.
// Use `Fast READ 0x0b` instead!
//#define CMD_READ		0x03
#define CMD_READ_STATUS		0x05
#define CMD_WRITE_ENABLE	0x06
#define CMD_FREAD			0x0b
#define CMD_SECTOR_ERASE	0x20
#define CMD_READ_SECURITY_REGS	0x48
#define CMD_READ_UNIQUE_ID	0x4b
#define CMD_READ_JEDEC_ID	0x9f
#define CMD_FREAD_DIO		0xbb

/*
 * Configure Memory Managed IO
 */
void flash_configure_mmio(void)
{
	// Set configuration for MMIO access by controller
	if (dio_enabled) {
		SFR_FLASH_MODEB = 0x18;
		SFR_FLASH_CMD_R = CMD_FREAD_DIO;	// By default we read with Dual speed
		SFR_FLASH_DUMMYCYCLES = 4;
		return;
	}

	SFR_FLASH_MODEB = 0x0;
	SFR_FLASH_CMD_R = CMD_FREAD; // Default is Single IO
	SFR_FLASH_DUMMYCYCLES = 8;
}


/*
 * Initializes the flash controller for programmed control
 * The configuration options are not really understood, the SPI speed
 * seems to be directly linked to the CPU frequency
 * This configures fast single IO at 20.8 MHz when the CPU clock is at 20.8MHz
 * and 62.5MHz when the CPU clock is configured at 125MHz
 */
void flash_init(uint8_t enable_dio)
{
	if (enable_dio) {
		SFR_FLASH_CONFIG = 9;  // There may be a chip-select in here
		SFR_FLASH_CONF_RCMD = CMD_FREAD_DIO;
		SFR_FLASH_CONF_DIV = 4;
	} else {
		// Configure fast read via divider = 8 and read-cmd being CMD_FREAD (for mmio)
		SFR_FLASH_CONFIG = 9;
		SFR_FLASH_CONF_RCMD = CMD_FREAD;
		SFR_FLASH_CONF_DIV = 8;
	}
	// Test Controller Busy
	while(SFR_FLASH_EXEC_BUSY);

	// Write 0 to status register
	SFR_FLASH_DUMMYCYCLES = 8;
	SFR_FLASH_MODEB = 0;
	SFR_FLASH_TCONF = 0x19;
	SFR_FLASH_CMD = CMD_WRITE_STATUS;
	SFR_FLASH_DATA0 = 0;
	SFR_FLASH_EXEC_GO = 1;
	while(SFR_FLASH_EXEC_BUSY);

	dio_enabled = enable_dio;
	flash_configure_mmio();
}


uint8_t flash_read_status(void)
{
	uint16_t t;

	// Test Controller Busy (we might call this directly after executing a command)
	t = 0;
	while(SFR_FLASH_EXEC_BUSY) {
		if (!++t) { print_string("[FS:EBUSY1]"); return 0xff; }
	}

	// setup status read command
	SFR_FLASH_TCONF = 0x11;
	SFR_FLASH_CMD_R = CMD_READ_STATUS;

	// execute and wait for controller done
	SFR_FLASH_EXEC_GO = 1;
	t = 0;
	while(SFR_FLASH_EXEC_BUSY) {
		if (!++t) { print_string("[FS:EBUSY2]"); return 0xff; }
	}

	/* This command clobbers CMD_R. If MMIO instruction fetch shares it,
	 * leaving 0x05 behind would corrupt code fetch right after we return, so
	 * restore the read command. flash_configure_mmio() only writes MODEB /
	 * CMD_R / DUMMYCYCLES and never touches DATA0, so reading the result
	 * afterwards is safe -- and saves a byte of the 128 bytes of internal RAM. */
	flash_configure_mmio();
	return SFR_FLASH_DATA0;
}


void flash_read_uid(void)
{
	while (flash_read_status() & 0x1);

	// Set slow read mode for UID
	SFR_FLASH_MODEB = 0x0;
	SFR_FLASH_CMD_R = CMD_READ_UNIQUE_ID;
	SFR_FLASH_DUMMYCYCLES = 8;

	// Transfer 4 bytes (command + 3 dummy bytes)
	SFR_FLASH_TCONF = 4;
	SFR_FLASH_ADDR16 = 0;
	SFR_FLASH_ADDR8 = 0;
	SFR_FLASH_ADDR0 = 0;

	SFR_FLASH_EXEC_GO = 1;
	while(SFR_FLASH_EXEC_BUSY);

	print_byte(SFR_FLASH_DATA0);
	print_byte(SFR_FLASH_DATA8);
	print_byte(SFR_FLASH_DATA16);
	print_byte(SFR_FLASH_DATA24);
	write_char(' ');

	SFR_FLASH_DUMMYCYCLES = 24;	// Doesn't seem to work; we get the same data as for the first transfer
	SFR_FLASH_EXEC_GO = 1;
	while(SFR_FLASH_EXEC_BUSY);

	print_byte(SFR_FLASH_DATA0);
	print_byte(SFR_FLASH_DATA8);
	print_byte(SFR_FLASH_DATA16);
	print_byte(SFR_FLASH_DATA24);

	flash_configure_mmio();
}

__code char* get_flash_size_str(void)
{
	switch (flash_capacity_code) {
		case 0x12: return "256 KB";
		case 0x13: return "512 KB";
		case 0x14: return "1 MB";
		case 0x15: return "2 MB";
		case 0x16: return "4 MB";
		case 0x17: return "8 MB";
		case 0x18: return "16 MB";
		default: return "unknown";
	}
}

void flash_read_jedecid(void)
{
	uint16_t i = 0;
	uint8_t st;

	/* Bounded: the original unconditional spin produced no output at all. */
	do {
		st = flash_read_status();
		if (!(st & 0x1))
			break;
		if (!(i & 0x3f))
			print_string("[JED:busy]");
	} while (++i);
	if (st & 0x1) {
		print_string("[JED:TIMEOUT st=0x"); print_byte(st);
		print_string("]\n");
	}

	// Set read mode for JEDEC ID
	SFR_FLASH_MODEB = 0x0;
	SFR_FLASH_CMD_R = CMD_READ_JEDEC_ID;
	SFR_FLASH_DUMMYCYCLES = 0;

	// Transfer 3 bytes back
	SFR_FLASH_TCONF = 0x13;

	SFR_FLASH_EXEC_GO = 1;
	i = 0;
	while(SFR_FLASH_EXEC_BUSY) {
		if (!++i) { print_string("[JED:EXEC-TIMEOUT]"); break; }
	}

	print_string("Flash information:\n");
	print_string("  Manufacturer ID: 0x");
	print_byte(SFR_FLASH_DATA0);
	print_string("\n  Memory Type:     0x");
	print_byte(SFR_FLASH_DATA8);
	print_string("\n  Capacity:        0x");
	flash_capacity_code = SFR_FLASH_DATA16;
	// A bogus capacity byte (0xff when MISO reads idle high) would make
	// flash_size garbage; fall back to 2 MB (HX25Q16) instead.
	if (flash_capacity_code < 0x12 || flash_capacity_code > 0x18)
		flash_capacity_code = 0x15;
	flash_size = 1UL << flash_capacity_code;
	print_byte(flash_capacity_code);
	print_string(" = "); print_string(get_flash_size_str()); write_char('\n');

	flash_configure_mmio();
}


void flash_write_enable(void)
{
	short status;

	// Wait until busy bit clear
	do {
		status = flash_read_status();
	} while (status & 0x1);

	SFR_FLASH_TCONF = 0x18;
	SFR_FLASH_CMD = CMD_WRITE_ENABLE;

	/* The following makes sure that the PAGE_PROGRAM command,
	 * where the data to be written follows the command word directly
	 * works properly
	 */
	SFR_FLASH_DUMMYCYCLES = 0;
	SFR_FLASH_MODEB = 0;

	SFR_FLASH_EXEC_GO = 1;
	// Wait for write status enabled
	do {
		status = flash_read_status();
	} while (!(status & 0x2));
}

/*
 * Reads bulk data of length len from the flash memory starging at address src
 * and writes the data into a buffer pointed to by dst in XMEM
 */
void flash_read_bulk(__xdata uint8_t *dst)
{
	short status;
	uint16_t i = 0;
	do {
		status = flash_read_status();
		if (!(status & 0x1))
			break;
		if (!++i) { print_string("[BULK:BUSY]"); break; }
	} while (1);

	// Set fast read mode
	if (dio_enabled) {
		SFR_FLASH_MODEB = 0x18;
		SFR_FLASH_CMD_R = CMD_FREAD_DIO;
		SFR_FLASH_DUMMYCYCLES = 4;
	} else {
		SFR_FLASH_MODEB = 0x0;
		SFR_FLASH_CMD_R = CMD_FREAD;	// Fast read
		SFR_FLASH_DUMMYCYCLES = 8;	// Add 8 dummy clocks
	}


	// Read 4 bytes
	while (1) {
		SFR_FLASH_ADDR16 = flash_region.addr >> 16;
		SFR_FLASH_ADDR8 = flash_region.addr >> 8;
		SFR_FLASH_ADDR0 = flash_region.addr;
		flash_region.addr += 4;

		SFR_FLASH_TCONF = 4;

		SFR_FLASH_EXEC_GO = 1;
		while(SFR_FLASH_EXEC_BUSY);

		*dst++ = SFR_FLASH_DATA0;
		if (flash_region.len == 1)
			break;
		*dst++ = SFR_FLASH_DATA8;
		if (flash_region.len == 2)
			break;
		*dst++ = SFR_FLASH_DATA16;
		if (flash_region.len == 3)
			break;
		*dst++ = SFR_FLASH_DATA24;
		if (flash_region.len == 4)
			break;
		flash_region.len -= 4;
	}
}


void flash_read_security(void)
{
	while (flash_read_status() & 0x1);

	// Set slow read mode
	SFR_FLASH_MODEB = 0x0;
	SFR_FLASH_CMD_R = CMD_READ_SECURITY_REGS;		// read security register
	SFR_FLASH_DUMMYCYCLES = 8;	// Add 8 dummy clocks as for fast read

	// Transfer 4 bytes (command + 3byte address)
	SFR_FLASH_TCONF = 4;
	do {
		SFR_FLASH_ADDR16 = flash_region.addr >> 16;
		SFR_FLASH_ADDR8 = flash_region.addr >> 8;
		SFR_FLASH_ADDR0 = flash_region.addr;
		flash_region.addr += 4;

		SFR_FLASH_EXEC_GO = 1;
		while(SFR_FLASH_EXEC_BUSY);

		print_byte(SFR_FLASH_DATA0);
		if (flash_region.len == 1)
			break;
		print_byte(SFR_FLASH_DATA8);
		if (flash_region.len == 2)
			break;
		print_byte(SFR_FLASH_DATA16);
		if (flash_region.len == 3)
			break;
		print_byte(SFR_FLASH_DATA24);
		write_char(' ');
		flash_region.len -= 4;
	} while(flash_region.len);

	flash_configure_mmio();
}


void flash_sector_erase(void)
{
	flash_write_enable();
	SFR_FLASH_TCONF = 8;
	SFR_FLASH_CMD = CMD_SECTOR_ERASE;

	SFR_FLASH_ADDR16 = flash_region.addr >> 16;
	SFR_FLASH_ADDR8 = flash_region.addr >> 8;
	SFR_FLASH_ADDR0 = flash_region.addr;

	SFR_FLASH_EXEC_GO = 1;
	while (flash_read_status() & 0x1);

	flash_configure_mmio();
}


void flash_write_bytes(__xdata uint8_t *ptr)
{
	// write_char('\n'); write_char('>'); print_long(flash_region.addr); write_char(':'); print_short(flash_region.len); write_char('-'); print_byte(*ptr); // write_char('\n');
	while(1) {
		flash_write_enable();
		SFR_FLASH_CMD = CMD_PAGE_PROGRAM;
		SFR_FLASH_TCONF = 0x40 | 8 | 4; // Bytes written is 4, 8 enables write, 0x40 is unknown
		// Last transfer?
		if (flash_region.len < 5) {
			SFR_FLASH_TCONF = 8 | flash_region.len;
		}

		SFR_FLASH_ADDR16 = flash_region.addr >> 16;
		SFR_FLASH_ADDR8 = flash_region.addr >> 8;
		SFR_FLASH_ADDR0 = flash_region.addr;
		SFR_FLASH_DATA0 = *ptr++;
		SFR_FLASH_DATA8 = *ptr++;
		SFR_FLASH_DATA16 = *ptr++;
		SFR_FLASH_DATA24 = *ptr++;

		// Execute transfer, we wait for completion at top of loop
		SFR_FLASH_EXEC_GO = 1;

		if (flash_region.len < 5)
			break;

		flash_region.len -= 4;
		flash_region.addr += 4;
	};
	while (flash_read_status() & 0x1);
	flash_configure_mmio();
}

/* ------------------------------------------------------------------
 * DEBUG: standalone flash controller / SPI chip diagnostics.
 *
 * Runs right after flash_init() from main() and reports the health of the
 * flash controller and the SPI chip instead of letting a dead, miswired or
 * overvolted chip hang the boot with zero output.
 *
 * RAM NOTE: the 8051 has only 128 bytes of internal RAM and the overlay
 * segment (OSEG) was already full -- adding this with ordinary locals made
 * the link fail with
 *     ?ASlink-Error-Could not get N consecutive bytes in internal RAM
 * So every piece of state here lives in XRAM and no helper takes pointer
 * parameters. Internal RAM cost of this whole block: zero.
 *
 * XIP NOTE: the CPU executes out of this very flash through MMIO, so any
 * change to MODEB / CMD_R / DUMMYCYCLES must be undone before returning.
 * The helpers below restore MMIO *before* returning; all printing happens
 * afterwards, from the caller.
 *
 * Self-contained on purpose: uses its own status read rather than
 * flash_read_status(), so it still works if that one is the thing broken.
 * ------------------------------------------------------------------ */

__xdata static uint8_t	fd_st;			/* last status / error flag */
__xdata static uint8_t	fd_mid, fd_typ, fd_cap;	/* last RDID bytes */
__xdata static uint16_t	fd_t;			/* timeout counter */
__xdata static uint8_t	fd_i;			/* loop counter */


/* Read the status register; result in fd_st (0xff = controller timeout). */
static void fdig_status(void)
{
	fd_t = 0;
	while (SFR_FLASH_EXEC_BUSY) {
		if (!++fd_t) { fd_st = 0xff; return; }
	}

	SFR_FLASH_TCONF = 0x11;
	SFR_FLASH_CMD_R = CMD_READ_STATUS;
	SFR_FLASH_EXEC_GO = 1;

	fd_t = 0;
	while (SFR_FLASH_EXEC_BUSY) {
		if (!++fd_t) { fd_st = 0xff; flash_configure_mmio(); return; }
	}

	fd_st = SFR_FLASH_DATA0;
	flash_configure_mmio();
}


/* Raw 3-byte JEDEC RDID (9Fh). dio=1 -> dual mode (0xbb), else single (0x0b).
 * Result in fd_mid/fd_typ/fd_cap; fd_st = 1 on success, 0 on timeout. */
static void fdig_rdid(uint8_t dio)
{
	fd_t = 0;
	while (SFR_FLASH_EXEC_BUSY) {
		if (!++fd_t) { fd_st = 0; return; }
	}

	if (dio) {
		SFR_FLASH_MODEB = 0x18;
		SFR_FLASH_CMD_R = CMD_FREAD_DIO;
		SFR_FLASH_DUMMYCYCLES = 4;
	} else {
		SFR_FLASH_MODEB = 0x0;
		SFR_FLASH_CMD_R = CMD_FREAD;
		SFR_FLASH_DUMMYCYCLES = 8;
	}

	/* 1 command byte out, 3 id bytes in */
	SFR_FLASH_TCONF = 0x13;
	SFR_FLASH_EXEC_GO = 1;

	fd_t = 0;
	while (SFR_FLASH_EXEC_BUSY) {
		if (!++fd_t) { fd_st = 0; flash_configure_mmio(); return; }
	}

	fd_mid = SFR_FLASH_DATA0;
	fd_typ = SFR_FLASH_DATA8;
	fd_cap = SFR_FLASH_DATA16;

	flash_configure_mmio();		/* restore XIP timing before returning */
	fd_st = 1;
}


void flash_diag(void)
{
	print_string("\n[FLASH-DIAG] controller:");
	print_string(" cfg=0x"); print_byte(SFR_FLASH_CONFIG);
	print_string(" div=0x"); print_byte(SFR_FLASH_CONF_DIV);
	print_string(" rcmd=0x"); print_byte(SFR_FLASH_CONF_RCMD);
	print_string(" modeb=0x"); print_byte(SFR_FLASH_MODEB);
	print_string(" dummy=0x"); print_byte(SFR_FLASH_DUMMYCYCLES);
	print_string(" dio="); write_char('0' + (dio_enabled & 1));
	write_char('\n');

	print_string("[FLASH-DIAG] status x4:");
	for (fd_i = 0; fd_i < 4; fd_i++) {
		fdig_status();
		print_string(" 0x"); print_byte(fd_st);
	}
	write_char('\n');

	if (fd_st == 0xff)
		print_string("[FLASH-DIAG] !! 0xff = MISO idle high, chip not answering\n");
	else if (fd_st & 0x01)
		print_string("[FLASH-DIAG] !! WIP stuck high, chip never completes\n");
	else if (fd_st & 0x02)
		print_string("[FLASH-DIAG] note: WEL already set\n");
	else
		print_string("[FLASH-DIAG] status idle, SPI link up\n");

	print_string("[FLASH-DIAG] rdid(dio):");
	fdig_rdid(1);
	if (fd_st) {
		print_string(" 0x"); print_byte(fd_mid);
		print_string(" 0x"); print_byte(fd_typ);
		print_string(" 0x"); print_byte(fd_cap);
		write_char('\n');
	} else
		print_string(" TIMEOUT\n");

	print_string("[FLASH-DIAG] rdid(single):");
	fdig_rdid(0);
	if (fd_st) {
		print_string(" 0x"); print_byte(fd_mid);
		print_string(" 0x"); print_byte(fd_typ);
		print_string(" 0x"); print_byte(fd_cap);
		write_char('\n');

		if (fd_mid == 0x5e && fd_typ == 0x60 && fd_cap == 0x15)
			print_string("[FLASH-DIAG] HX25Q16 id OK (5e 60 15)\n");
		else if (fd_mid == 0x0e && fd_typ == 0x40 && fd_cap == 0x15)
			print_string("[FLASH-DIAG] id 0e 40 15 (datasheet says 5e 60 15)\n");
		else if (fd_mid == 0xff)
			print_string("[FLASH-DIAG] !! all-ff: no chip response\n");
		else if (fd_mid == 0x00)
			print_string("[FLASH-DIAG] !! all-00: MISO held low / shorted\n");
		else
			print_string("[FLASH-DIAG] unexpected id\n");
	} else
		print_string(" TIMEOUT\n");

	print_string("[FLASH-DIAG] done\n");
}
