# light_exporter.py
"""Core .light archive export logic (no Blender dependency)."""
import struct
import io
from typing import List

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

from .jpeg_tables import make_ijl_stream, QT_LUM_ZIG, QT_CHROM_ZIG


def tile_atlas_to_streams(atlas_pil: Image.Image, grid: int,
                          tile_size: int, quality: int) -> List[bytes]:
    """
    Slice a Pillow atlas image into grid×grid tiles, compress each with
    IJL tables, and return a list of byte strings (IJL streams).
    Tiles are ordered row‑major (left‑to‑right, top‑to‑bottom).
    """
    if not PIL_AVAILABLE:
        raise RuntimeError("Pillow is required for .light export")
    tiles = []
    for ty in range(grid):
        for tx in range(grid):
            left = tx * tile_size
            upper = ty * tile_size
            tile = atlas_pil.crop((left, upper, left + tile_size, upper + tile_size))
            # Encode to JPEG with exact IJL tables
            buf = io.BytesIO()
            tile.save(buf, format='JPEG', quality=quality,
                      qtables=[QT_LUM_ZIG, QT_CHROM_ZIG])
            stream = make_ijl_stream(buf.getvalue(), quality)
            tiles.append(stream)
    return tiles


def calculate_clipmap_count(grid: int, tile_number: int,
                            stride1: int, stride2: int) -> int:
    """Calculate the number of clipmap tiles (num2) as the game does."""
    eff = tile_number - 2
    tiles1 = (grid * eff) // stride1 + 1
    tiles2 = (grid * eff) // stride2 + 1
    return tiles1 * tiles2