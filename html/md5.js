// Minimal MD5 (RFC 1321) over a Uint8Array.
// crypto.subtle is unavailable over plain http (non-secure context),
// so the browser computes the digest itself.
function md5Bytes(input) {
  var K = [
    0xd76aa478,0xe8c7b756,0x242070db,0xc1bdceee,0xf57c0faf,0x4787c62a,
    0xa8304613,0xfd469501,0x698098d8,0x8b44f7af,0xffff5bb1,0x895cd7be,
    0x6b901122,0xfd987193,0xa679438e,0x49b40821,0xf61e2562,0xc040b340,
    0x265e5a51,0xe9b6c7aa,0xd62f105d,0x02441453,0xd8a1e681,0xe7d3fbc8,
    0x21e1cde6,0xc33707d6,0xf4d50d87,0x455a14ed,0xa9e3e905,0xfcefa3f8,
    0x676f02d9,0x8d2a4c8a,0xfffa3942,0x8771f681,0x6d9d6122,0xfde5380c,
    0xa4beea44,0x4bdecfa9,0xf6bb4b60,0xbebfbc70,0x289b7ec6,0xeaa127fa,
    0xd4ef3085,0x04881d05,0xd9d4d039,0xe6db99e5,0x1fa27cf8,0xc4ac5665,
    0xf4292244,0x432aff97,0xab9423a7,0xfc93a039,0x655b59c3,0x8f0ccc92,
    0xffeff47d,0x85845dd1,0x6fa87e4f,0xfe2ce6e0,0xa3014314,0x4e0811a1,
    0xf7537e82,0xbd3af235,0x2ad7d2bb,0xeb86d391];
  var S = [7,12,17,22,7,12,17,22,7,12,17,22,7,12,17,22,
           5,9,14,20,5,9,14,20,5,9,14,20,5,9,14,20,
           4,11,16,23,4,11,16,23,4,11,16,23,4,11,16,23,
           6,10,15,21,6,10,15,21,6,10,15,21,6,10,15,21];

  var len = input.length;
  var bitLen = len * 8;
  var withPad = len + 1;
  var rem = withPad % 64;
  var padLen = rem <= 56 ? (56 - rem) : (56 + 64 - rem);
  var total = withPad + padLen + 8;
  var m = new Uint8Array(total);
  m.set(input, 0);
  m[len] = 0x80;
  m[total - 8] = bitLen & 0xff;
  m[total - 7] = (bitLen >>> 8) & 0xff;
  m[total - 6] = (bitLen >>> 16) & 0xff;
  m[total - 5] = (bitLen >>> 24) & 0xff;

  var a0 = 0x67452301, b0 = 0xefcdab89, c0 = 0x98badcfe, d0 = 0x10325476;

  function rotl(x, n) { return (x << n) | (x >>> (32 - n)); }

  for (var off = 0; off < total; off += 64) {
    var M = new Int32Array(16);
    for (var j = 0; j < 16; j++) {
      M[j] = (m[off + j*4]) | (m[off + j*4 + 1] << 8) |
             (m[off + j*4 + 2] << 16) | (m[off + j*4 + 3] << 24);
    }
    var A = a0, B = b0, C = c0, D = d0;
    for (var i = 0; i < 64; i++) {
      var F, g;
      if (i < 16)      { F = (B & C) | (~B & D); g = i; }
      else if (i < 32) { F = (D & B) | (~D & C); g = (5*i + 1) & 15; }
      else if (i < 48) { F = B ^ C ^ D;          g = (3*i + 5) & 15; }
      else             { F = C ^ (B | ~D);       g = (7*i) & 15; }
      F = (F + A + K[i] + M[g]) | 0;
      A = D; D = C; C = B;
      B = (B + rotl(F, S[i])) | 0;
    }
    a0 = (a0 + A) | 0; b0 = (b0 + B) | 0;
    c0 = (c0 + C) | 0; d0 = (d0 + D) | 0;
  }

  // Digests are emitted little-endian: the low byte of a0 comes first.
  function hex(n) {
    var s = '';
    for (var i = 0; i < 4; i++) {
      var b = (n >>> (i * 8)) & 0xff;
      s += (b < 16 ? '0' : '') + b.toString(16);
    }
    return s;
  }
  return hex(a0) + hex(b0) + hex(c0) + hex(d0);
}
