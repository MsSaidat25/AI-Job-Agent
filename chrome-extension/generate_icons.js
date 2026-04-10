/**
 * Generate PNG icon files for the Chrome extension.
 * Run with: node generate_icons.js
 */

const fs = require('fs');
const zlib = require('zlib');
const path = require('path');

function createPNG(size) {
  const width = size;
  const height = size;
  const accent = [242, 204, 13];
  const bg = [34, 34, 34];

  // Build raw pixel data (RGBA, filter byte per row)
  const rawRows = [];
  for (let y = 0; y < height; y++) {
    const row = [0]; // filter: none
    for (let x = 0; x < width; x++) {
      const nx = x / width;
      const ny = y / height;
      let r = bg[0], g = bg[1], b = bg[2], a = 255;

      // Briefcase body
      if (nx >= 0.15 && nx <= 0.85 && ny >= 0.35 && ny <= 0.80) {
        [r, g, b] = accent;
      }
      // Handle
      if (nx >= 0.35 && nx <= 0.65 && ny >= 0.15 && ny <= 0.40) {
        [r, g, b] = accent;
      }
      // Handle inner cutout
      if (nx >= 0.42 && nx <= 0.58 && ny >= 0.22 && ny <= 0.35) {
        [r, g, b] = bg;
      }
      // Clasp
      if (nx >= 0.42 && nx <= 0.58 && ny >= 0.50 && ny <= 0.62) {
        r = Math.floor(accent[0] * 0.7);
        g = Math.floor(accent[1] * 0.7);
        b = Math.floor(accent[2] * 0.7);
      }
      // Circular mask
      const cx = width / 2, cy = height / 2;
      const dist = Math.sqrt((x - cx) ** 2 + (y - cy) ** 2);
      if (dist > width * 0.48) a = 0;

      row.push(r, g, b, a);
    }
    rawRows.push(Buffer.from(row));
  }

  const rawData = Buffer.concat(rawRows);
  const compressed = zlib.deflateSync(rawData, { level: 9 });

  // Build PNG chunks
  function writeU32BE(val) {
    const buf = Buffer.alloc(4);
    buf.writeUInt32BE(val, 0);
    return buf;
  }

  function makeChunk(type, data) {
    const typeBuf = Buffer.from(type, 'ascii');
    const crcData = Buffer.concat([typeBuf, data]);
    const crc = crc32(crcData);
    return Buffer.concat([writeU32BE(data.length), typeBuf, data, writeU32BE(crc)]);
  }

  // CRC32 table
  const crcTable = new Uint32Array(256);
  for (let n = 0; n < 256; n++) {
    let c = n;
    for (let k = 0; k < 8; k++) {
      c = (c & 1) ? (0xEDB88320 ^ (c >>> 1)) : (c >>> 1);
    }
    crcTable[n] = c;
  }

  function crc32(buf) {
    let crc = 0xFFFFFFFF;
    for (let i = 0; i < buf.length; i++) {
      crc = crcTable[(crc ^ buf[i]) & 0xFF] ^ (crc >>> 8);
    }
    return (crc ^ 0xFFFFFFFF) >>> 0;
  }

  // IHDR
  const ihdr = Buffer.alloc(13);
  ihdr.writeUInt32BE(width, 0);
  ihdr.writeUInt32BE(height, 4);
  ihdr[8] = 8;  // bit depth
  ihdr[9] = 6;  // color type: RGBA
  ihdr[10] = 0; // compression
  ihdr[11] = 0; // filter
  ihdr[12] = 0; // interlace

  const signature = Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]);

  return Buffer.concat([
    signature,
    makeChunk('IHDR', ihdr),
    makeChunk('IDAT', compressed),
    makeChunk('IEND', Buffer.alloc(0)),
  ]);
}

// Ensure icons directory exists
const iconsDir = path.join(__dirname, 'icons');
if (!fs.existsSync(iconsDir)) {
  fs.mkdirSync(iconsDir, { recursive: true });
}

for (const size of [16, 48, 128]) {
  const png = createPNG(size);
  const filePath = path.join(iconsDir, `icon${size}.png`);
  fs.writeFileSync(filePath, png);
  console.log(`Created ${filePath} (${png.length} bytes)`);
}
