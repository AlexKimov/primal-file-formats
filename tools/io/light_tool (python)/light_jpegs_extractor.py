#!/usr/bin/env python3
"""

Usage: python extract_light_final.py <input.light> [output_dir]
"""

import struct
import sys
import os
from PIL import Image
import io


QT_LUM_ROW = bytes([
    3,  2,  2,  3,  5,  8, 10, 12,
    2,  2,  3,  4,  5, 12, 12, 11,
    3,  3,  3,  5,  8, 11, 14, 11,
    3,  3,  4,  6, 10, 17, 16, 12,
    4,  4,  7, 11, 14, 22, 21, 15,
    5,  7, 11, 13, 16, 21, 23, 18,
   10, 13, 16, 17, 21, 24, 24, 20,
   14, 18, 19, 20, 22, 20, 21, 20
])

QT_CHROM_ROW = bytes([
    3,  4,  5,  9, 20, 20, 20, 20,
    4,  4,  5, 13, 20, 20, 20, 20,
    5,  5, 11, 20, 20, 20, 20, 20,
    9, 13, 20, 20, 20, 20, 20, 20,
   20, 20, 20, 20, 20, 20, 20, 20,
   20, 20, 20, 20, 20, 20, 20, 20,
   20, 20, 20, 20, 20, 20, 20, 20,
   20, 20, 20, 20, 20, 20, 20, 20
])

def rowmajor_to_zigzag(block):
    """Convert an 8x8 block from row major to JPEG zigzag order."""
    zigzag = [
         0,  1,  8, 16,  9,  2,  3, 10,
        17, 24, 32, 25, 18, 11,  4,  5,
        12, 19, 26, 33, 40, 48, 41, 34,
        27, 20, 13,  6,  7, 14, 21, 28,
        35, 42, 49, 56, 57, 50, 43, 36,
        29, 22, 15, 23, 30, 37, 44, 51,
        58, 59, 52, 45, 38, 31, 39, 46,
        53, 60, 61, 54, 47, 55, 62, 63
    ]
    if len(block) != 64:
        raise ValueError("Quantization table must have 64 entries")
    return bytes(block[zigzag[i]] for i in range(64))

QT_LUM_ZIG = rowmajor_to_zigzag(QT_LUM_ROW)
QT_CHROM_ZIG = rowmajor_to_zigzag(QT_CHROM_ROW)

# ----------------------------------------------------------------------
# 2. Standard Huffman tables (exactly match reference JPEG)
# ----------------------------------------------------------------------

HUFF_DC_LUM   = ([0x00,0x01,0x05,0x01,0x01,0x01,0x01,0x01,0x01,0x00,0x00,0x00,0x00,0x00,0x00,0x00],
                 [0x00,0x01,0x02,0x03,0x04,0x05,0x06,0x07,0x08,0x09,0x0A,0x0B])
HUFF_DC_CHROM = ([0x00,0x03,0x01,0x01,0x01,0x01,0x01,0x01,0x01,0x01,0x01,0x00,0x00,0x00,0x00,0x00],
                 [0x00,0x01,0x02,0x03,0x04,0x05,0x06,0x07,0x08,0x09,0x0A,0x0B])
HUFF_AC_LUM   = ([0x00,0x02,0x01,0x03,0x03,0x02,0x04,0x03,0x05,0x05,0x04,0x04,0x00,0x00,0x01,0x7D],
                 [0x01,0x02,0x03,0x00,0x04,0x11,0x05,0x12,0x21,0x31,0x41,0x06,0x13,0x51,0x61,0x07,
                  0x22,0x71,0x14,0x32,0x81,0x91,0xA1,0x08,0x23,0x42,0xB1,0xC1,0x15,0x52,0xD1,0xF0,
                  0x24,0x33,0x62,0x72,0x82,0x09,0x0A,0x16,0x17,0x18,0x19,0x1A,0x25,0x26,0x27,0x28,
                  0x29,0x2A,0x34,0x35,0x36,0x37,0x38,0x39,0x3A,0x43,0x44,0x45,0x46,0x47,0x48,0x49,
                  0x4A,0x53,0x54,0x55,0x56,0x57,0x58,0x59,0x5A,0x63,0x64,0x65,0x66,0x67,0x68,0x69,
                  0x6A,0x73,0x74,0x75,0x76,0x77,0x78,0x79,0x7A,0x83,0x84,0x85,0x86,0x87,0x88,0x89,
                  0x8A,0x92,0x93,0x94,0x95,0x96,0x97,0x98,0x99,0x9A,0xA2,0xA3,0xA4,0xA5,0xA6,0xA7,
                  0xA8,0xA9,0xAA,0xB2,0xB3,0xB4,0xB5,0xB6,0xB7,0xB8,0xB9,0xBA,0xC2,0xC3,0xC4,0xC5,
                  0xC6,0xC7,0xC8,0xC9,0xCA,0xD2,0xD3,0xD4,0xD5,0xD6,0xD7,0xD8,0xD9,0xDA,0xE1,0xE2,
                  0xE3,0xE4,0xE5,0xE6,0xE7,0xE8,0xE9,0xEA,0xF1,0xF2,0xF3,0xF4,0xF5,0xF6,0xF7,0xF8,
                  0xF9,0xFA])
HUFF_AC_CHROM = ([0x00,0x02,0x01,0x02,0x04,0x04,0x03,0x04,0x07,0x05,0x04,0x04,0x00,0x01,0x02,0x77],
                 [0x00,0x01,0x02,0x03,0x11,0x04,0x05,0x21,0x31,0x06,0x12,0x41,0x51,0x07,0x61,0x71,
                  0x13,0x22,0x32,0x81,0x08,0x14,0x42,0x91,0xA1,0xB1,0xC1,0x09,0x23,0x33,0x52,0xF0,
                  0x15,0x62,0x72,0xD1,0x0A,0x16,0x24,0x34,0xE1,0x25,0xF1,0x17,0x18,0x19,0x1A,0x26,
                  0x27,0x28,0x29,0x2A,0x35,0x36,0x37,0x38,0x39,0x3A,0x43,0x44,0x45,0x46,0x47,0x48,
                  0x49,0x4A,0x53,0x54,0x55,0x56,0x57,0x58,0x59,0x5A,0x63,0x64,0x65,0x66,0x67,0x68,
                  0x69,0x6A,0x73,0x74,0x75,0x76,0x77,0x78,0x79,0x7A,0x82,0x83,0x84,0x85,0x86,0x87,
                  0x88,0x89,0x8A,0x92,0x93,0x94,0x95,0x96,0x97,0x98,0x99,0x9A,0xA2,0xA3,0xA4,0xA5,
                  0xA6,0xA7,0xA8,0xA9,0xAA,0xB2,0xB3,0xB4,0xB5,0xB6,0xB7,0xB8,0xB9,0xBA,0xC2,0xC3,
                  0xC4,0xC5,0xC6,0xC7,0xC8,0xC9,0xCA,0xD2,0xD3,0xD4,0xD5,0xD6,0xD7,0xD8,0xD9,0xDA,
                  0xE2,0xE3,0xE4,0xE5,0xE6,0xE7,0xE8,0xE9,0xEA,0xF2,0xF3,0xF4,0xF5,0xF6,0xF7,0xF8,
                  0xF9,0xFA])

# ----------------------------------------------------------------------
# 3. Build a complete JPEG header (matching the reference exactly)
# ----------------------------------------------------------------------

def build_jpeg_header(width, height):
    """Create a JPEG header with APP0, COM, DQT, DHT, SOF0, SOS."""
    def _dht(tc, th, bits, values):
        header = b'\xff\xc4'
        length = 2 + 1 + 16 + len(values)
        return header + struct.pack('>H', length) + bytes([(tc << 4) | th]) + bytes(bits) + bytes(values)

    jpeg = b'\xff\xd8'  # SOI

    # APP0 (JFIF)
    app0 = b'\xff\xe0' + struct.pack('>H', 16)
    app0 += b'JFIF\x00'  # identifier + null
    app0 += struct.pack('>BBBB', 1, 1, 1, 0)  # version (1.1), density (1x1), thumbnail none
    jpeg += app0

    # COM (Intel JPEG Library comment)
    # comment = b'Intel(R) JPEG Library, version [1.51.12.44].'
    # com = b'\xff\xfe' + struct.pack('>H', 2 + len(comment)) + comment
    # jpeg += com

    # DQT
    jpeg += b'\xff\xdb' + struct.pack('>H', 2 + 1+64 + 1+64)
    jpeg += b'\x00' + QT_LUM_ZIG
    jpeg += b'\x01' + QT_CHROM_ZIG

    # DHT
    jpeg += _dht(0, 0, *HUFF_DC_LUM)
    jpeg += _dht(1, 0, *HUFF_AC_LUM)
    jpeg += _dht(0, 1, *HUFF_DC_CHROM)
    jpeg += _dht(1, 1, *HUFF_AC_CHROM)

    # SOF0
    sof0 = b'\xff\xc0' + struct.pack('>H', 8 + 3*3)
    sof0 += b'\x08'                                # precision 8
    sof0 += struct.pack('>H', height)
    sof0 += struct.pack('>H', width)
    sof0 += b'\x03'                                # 3 components
    sof0 += b'\x01\x11\x00'   # Y: 1x1, Q-table 0
    sof0 += b'\x02\x11\x01'   # Cb: 1x1, Q-table 1
    sof0 += b'\x03\x11\x01'   # Cr: 1x1, Q-table 1
    jpeg += sof0

    # SOS
    sos = b'\xff\xda' + struct.pack('>H', 6 + 2*3)
    sos += b'\x03'            # 3 components
    sos += b'\x01\x00'        # Y: DC/AC table 0
    sos += b'\x02\x11'        # Cb: DC/AC table 1
    sos += b'\x03\x11'        # Cr: DC/AC table 1
    sos += b'\x00\x3f\x00'    # spectral selection 0..63, approx 0
    jpeg += sos

    return jpeg

# ----------------------------------------------------------------------
# 4. Extract raw scan data from a partial JPEG chunk
# ----------------------------------------------------------------------

def extract_scan_data(raw_chunk):
    """Return the compressed scan data (between SOS and EOI)."""
    if raw_chunk[:2] != b'\xff\xd8':
        return raw_chunk   # already pure scan
    sos_pos = raw_chunk.find(b'\xff\xda')
    if sos_pos == -1:
        raise ValueError("SOS marker not found")
    length = struct.unpack('>H', raw_chunk[sos_pos+2:sos_pos+4])[0]
    scan_start = sos_pos + 2 + length
    if raw_chunk[-2:] == b'\xff\xd9':
        return raw_chunk[scan_start:-2]
    return raw_chunk[scan_start:]

def parse_light(filepath):
    with open(filepath, 'rb') as f:
        magic = f.read(11)
        if magic != b'DragonLight':
            raise ValueError(f"Bad magic: got {magic}")
        unk           = struct.unpack('<I', f.read(4))[0]
        tileNumber    = struct.unpack('<I', f.read(4))[0]
        tilesInRow    = struct.unpack('<I', f.read(4))[0]
        format_d3d    = struct.unpack('<I', f.read(4))[0]
        dayParts      = struct.unpack('<I', f.read(4))[0]
        f.seek(dayParts * 16, 1)
        subsampling1  = struct.unpack('<I', f.read(4))[0]
        jquality1     = struct.unpack('<I', f.read(4))[0]
        subsampling2  = struct.unpack('<I', f.read(4))[0]
        jquality2     = struct.unpack('<I', f.read(4))[0]
        subsampling3  = struct.unpack('<I', f.read(4))[0]
        jquality3     = struct.unpack('<I', f.read(4))[0]
        clipmapStride1 = struct.unpack('<I', f.read(4))[0]
        clipmapStride2 = struct.unpack('<I', f.read(4))[0]

        num1 = dayParts * tilesInRow * tilesInRow
        tmp_w = tilesInRow * (tileNumber - 2) // clipmapStride1 + 1
        tmp_h = tilesInRow * (tileNumber - 2) // clipmapStride2 + 1
        num2 = dayParts * tmp_w * tmp_h

        jpegStreamSize1 = [struct.unpack('<I', f.read(4))[0] for _ in range(num1)]
        size1 = struct.unpack('<I', f.read(4))[0]
        jpegStreamSize2 = [struct.unpack('<I', f.read(4))[0] for _ in range(num2)]

        return {
            'tileNumber': tileNumber,
            'num1': num1,
            'jpegStreamSize1': jpegStreamSize1,
            'jquality1': jquality1,
            'data_start_offset': f.tell()
        }

def extract_tiles(light_path, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    info = parse_light(light_path)
    tile_w = info['tileNumber']
    tile_h = tile_w
    quality = info['jquality1']

    with open(light_path, 'rb') as f:
        f.seek(info['data_start_offset'])
        for i in range(info['num1']):
            size = info['jpegStreamSize1'][i]
            raw_chunk = f.read(size)

            # If the chunk already contains a DQT, it's a complete JPEG – still
            # re-encode for consistency (like the original tool), but we can
            # also just pass it through. We'll always rebuild the header to be safe.
            scan = extract_scan_data(raw_chunk)
            header = build_jpeg_header(tile_w, tile_h)
            jpeg_bytes = header + scan + b'\xff\xd9'

            try:
                img = Image.open(io.BytesIO(jpeg_bytes))
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                out_path = os.path.join(output_dir, f"tile_{i:04d}.jpg")
                img.save(out_path, "JPEG", quality=quality)
                print(f"[{i+1}/{info['num1']}] {out_path} saved "
                      f"({tile_w}x{tile_h}, q={quality})")
            except Exception as e:
                print(f"  [!] Tile {i} failed: {e}")
                # Fallback: write the reconstructed bytes
                fb_path = os.path.join(output_dir, f"tile_{i:04d}_reconstructed.jpg")
                with open(fb_path, 'wb') as fb:
                    fb.write(jpeg_bytes)
                print(f"      -> saved reconstructed JPEG as {fb_path}")

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <input.light> [output_dir]")
        sys.exit(1)
    in_file = sys.argv[1]
    out = sys.argv[2] if len(sys.argv) > 2 else "."
    extract_tiles(in_file, out)