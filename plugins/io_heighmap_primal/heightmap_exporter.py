# heightmap_exporter.py
"""Core .land heightmap export logic (no Blender dependency)."""
import struct
from typing import List, Tuple

from .binary_reader import BinaryReader
from .binary_writer import BinaryWriter


def read_land_template(path: str) -> Tuple[bytes, int, int]:
    """
    Parse a .land template file and return:
      - prefix: all bytes before the height array
      - width, height: dimension of the height grid
      - suffix: all bytes after the height array
    """
    r = BinaryReader(path)
    # Magic + skip header fields to reach pnumber
    r.read_bytes(10)                    # magic
    r.read_u32(); r.read_u32(); r.read_u32()   # 3 unused uint32
    r.read_u16(); r.read_u16(); r.read_u16(); r.read_u16()  # 4 unused uint16
    r.read_u32()                        # code1
    r.read_u16()                        # size (unused)
    pnumber = r.read_u16()              # grid dimension
    r.read_u16()                        # unk
    # Now at the start of the height array
    height_start = r.tell()
    r.close()

    # Read the whole file
    with open(path, 'rb') as f:
        data = f.read()

    prefix = data[:height_start]
    height_len = pnumber * pnumber * 2   # int16
    suffix = data[height_start + height_len:]

    return prefix, pnumber, pnumber, suffix


def build_height_array(vertices, width: int, height: int, height_scale: float) -> List[int]:
    """
    Extract vertex Z values, reverse the scale, and clamp to int16 range.
    vertices: Blender mesh vertices (access by index).
    """
    if len(vertices) != width * height:
        raise ValueError(f"Vertex count {len(vertices)} does not match {width}x{height}")

    heights = []
    for v in vertices:
        h = int(round(v.co.z / height_scale))
        if h < -32768: h = -32768
        if h > 32767: h = 32767
        heights.append(h)
    return heights


def write_land_file(output_path: str, prefix: bytes, heights: List[int], suffix: bytes) -> None:
    """Assemble and write the final .land file."""
    writer = BinaryWriter()
    writer.write_bytes(prefix)
    writer.write_array('h', heights)
    writer.write_bytes(suffix)
    with open(output_path, 'wb') as f:
        f.write(writer.to_bytes())