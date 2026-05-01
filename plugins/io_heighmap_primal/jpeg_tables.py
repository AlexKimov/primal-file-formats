# jpeg_tables.py
"""Shared JPEG tables, header building, and stream manipulation for Primal .light files."""

import struct
import io
from typing import List, Tuple, Optional

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

# ----------------------------------------------------------------------
# Exact IJL quantization tables (row‑major)
# ----------------------------------------------------------------------
_QT_LUM_ROW = [
    3,  2,  2,  3,  5,  8, 10, 12,
    2,  2,  3,  4,  5, 12, 12, 11,
    3,  3,  3,  5,  8, 11, 14, 11,
    3,  3,  4,  6, 10, 17, 16, 12,
    4,  4,  7, 11, 14, 22, 21, 15,
    5,  7, 11, 13, 16, 21, 23, 18,
   10, 13, 16, 17, 21, 24, 24, 20,
   14, 18, 19, 20, 22, 20, 21, 20
]

_QT_CHROM_ROW = [
    3,  4,  5,  9, 20, 20, 20, 20,
    4,  4,  5, 13, 20, 20, 20, 20,
    5,  5, 11, 20, 20, 20, 20, 20,
    9, 13, 20, 20, 20, 20, 20, 20,
   20, 20, 20, 20, 20, 20, 20, 20,
   20, 20, 20, 20, 20, 20, 20, 20,
   20, 20, 20, 20, 20, 20, 20, 20,
   20, 20, 20, 20, 20, 20, 20, 20
]

# Zigzag mapping for 8×8 blocks
_ZIGZAG = (
     0,  1,  8, 16,  9,  2,  3, 10,
    17, 24, 32, 25, 18, 11,  4,  5,
    12, 19, 26, 33, 40, 48, 41, 34,
    27, 20, 13,  6,  7, 14, 21, 28,
    35, 42, 49, 56, 57, 50, 43, 36,
    29, 22, 15, 23, 30, 37, 44, 51,
    58, 59, 52, 45, 38, 31, 39, 46,
    53, 60, 61, 54, 47, 55, 62, 63
)

def row_to_zigzag(block: List[int]) -> List[int]:
    return [block[i] for i in _ZIGZAG]

# Quantization tables in zigzag order (ready for DQT markers)
QT_LUM_ZIG = row_to_zigzag(_QT_LUM_ROW)
QT_CHROM_ZIG = row_to_zigzag(_QT_CHROM_ROW)

# ----------------------------------------------------------------------
# Standard Huffman tables (exactly matching IJL defaults)
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
# JPEG marker building helpers
# ----------------------------------------------------------------------
def _make_dht(tc: int, th: int, bits: list, values: list) -> bytes:
    """Build a single DHT (Define Huffman Table) segment."""
    header = b'\xff\xc4'
    length = 2 + 1 + 16 + len(values)
    return header + struct.pack('>H', length) + bytes([(tc << 4) | th]) + bytes(bits) + bytes(values)

def build_full_header(width: int, height: int) -> bytes:
    """
    Build a complete JPEG header (SOI..SOS) with APP0, COM, DQT, DHT,
    using the exact IJL quantization and Huffman tables.
    The returned bytes must be followed by scan data and an EOI marker.
    """
    jpeg = b'\xff\xd8'
    # APP0
    jpeg += b'\xff\xe0' + struct.pack('>H', 16)
    jpeg += b'JFIF\x00'
    jpeg += struct.pack('>BBBB', 1, 1, 1, 0)
    # COM
    comment = b'Intel(R) JPEG Library, version [1.51.12.44].'
    jpeg += b'\xff\xfe' + struct.pack('>H', 2 + len(comment)) + comment
    # DQT
    jpeg += b'\xff\xdb' + struct.pack('>H', 2 + 1 + 64 + 1 + 64)
    jpeg += b'\x00' + bytes(QT_LUM_ZIG)
    jpeg += b'\x01' + bytes(QT_CHROM_ZIG)
    # DHT
    jpeg += _make_dht(0, 0, *HUFF_DC_LUM)
    jpeg += _make_dht(1, 0, *HUFF_AC_LUM)
    jpeg += _make_dht(0, 1, *HUFF_DC_CHROM)
    jpeg += _make_dht(1, 1, *HUFF_AC_CHROM)
    # SOF0
    sof0 = b'\xff\xc0' + struct.pack('>H', 8 + 3 * 3)
    sof0 += b'\x08'
    sof0 += struct.pack('>H', height)
    sof0 += struct.pack('>H', width)
    sof0 += b'\x03'
    sof0 += b'\x01\x11\x00'
    sof0 += b'\x02\x11\x01'
    sof0 += b'\x03\x11\x01'
    jpeg += sof0
    # SOS
    sos = b'\xff\xda' + struct.pack('>H', 6 + 2 * 3)
    sos += b'\x03'
    sos += b'\x01\x00'
    sos += b'\x02\x11'
    sos += b'\x03\x11'
    sos += b'\x00\x3f\x00'
    jpeg += sos
    return jpeg

# ----------------------------------------------------------------------
# Scan data extraction
# ----------------------------------------------------------------------
def extract_scan_data(raw: bytes) -> bytes:
    """
    Extract the pure entropy‑coded scan data from a partial JPEG stream.
    If the data does not begin with SOI, it is assumed to be raw scan data and returned unchanged.
    """
    if raw[:2] != b'\xff\xd8':
        return raw
    sos_pos = raw.find(b'\xff\xda')
    if sos_pos == -1:
        return raw[2:]   # skip SOI as fallback
    length = struct.unpack('>H', raw[sos_pos+2:sos_pos+4])[0]
    scan_start = sos_pos + 2 + length
    eoi_pos = raw.find(b'\xff\xd9', scan_start)
    if eoi_pos != -1:
        return raw[scan_start:eoi_pos]
    return raw[scan_start:]

# ----------------------------------------------------------------------
# Re‑encode a JPEG with the exact IJL tables
# ----------------------------------------------------------------------
def reencode_with_ijl(data: bytes, quality: int = 90) -> Optional[bytes]:
    """
    Decode a JPEG, re‑encode it using the IJL quantization tables,
    and return the new JPEG bytes. Falls back to the input data if Pillow is missing.
    """
    if not PIL_AVAILABLE:
        return data
    try:
        img = Image.open(io.BytesIO(data))
        if img.mode != 'RGB':
            img = img.convert('RGB')
        out = io.BytesIO()
        img.save(out, format='JPEG', quality=quality,
                 qtables=[QT_LUM_ZIG, QT_CHROM_ZIG])
        return out.getvalue()
    except Exception:
        return data

# ----------------------------------------------------------------------
# Create an IJL stream (no DQT/DHT) from a standard JPEG
# ----------------------------------------------------------------------
def make_ijl_stream(img_bytes: bytes, quality: int = 90) -> bytes:
    """
    Take a standard JPEG image (as bytes), re‑encode with the IJL tables,
    then strip the DQT/DHT markers to produce the game's raw stream format.
    Returns bytes: SOI + SOF0 + SOS + scan + EOI.
    """
    if not PIL_AVAILABLE:
        raise RuntimeError("Pillow is required for .light export")

    img = Image.open(io.BytesIO(img_bytes))
    if img.mode != 'RGB':
        img = img.convert('RGB')

    # Re‑encode with custom tables
    buf = io.BytesIO()
    img.save(buf, format='JPEG', quality=quality,
             qtables=[QT_LUM_ZIG, QT_CHROM_ZIG])
    jpeg = buf.getvalue()

    # Locate markers
    sof0_pos = jpeg.find(b'\xff\xc0')
    if sof0_pos == -1:
        raise ValueError("SOF0 missing in re‑encoded JPEG")
    sof0_len = struct.unpack('>H', jpeg[sof0_pos+2:sof0_pos+4])[0]
    sof0_seg = jpeg[sof0_pos:sof0_pos+2+sof0_len]

    sos_pos = jpeg.find(b'\xff\xda')
    if sos_pos == -1:
        raise ValueError("SOS missing in re‑encoded JPEG")
    sos_len = struct.unpack('>H', jpeg[sos_pos+2:sos_pos+4])[0]
    sos_seg = jpeg[sos_pos:sos_pos+2+sos_len]

    scan_start = sos_pos + 2 + sos_len
    eoi_pos = jpeg.find(b'\xff\xd9', scan_start)
    if eoi_pos == -1:
        eoi_pos = len(jpeg) - 2
    scan = jpeg[scan_start:eoi_pos]

    return b'\xff\xd8' + sof0_seg + sos_seg + scan + b'\xff\xd9'