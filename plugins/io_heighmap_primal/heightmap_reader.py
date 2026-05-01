# heightmap_reader.py
"""Parser for .land heightmap files."""
from dataclasses import dataclass, field
from typing import List, Optional, BinaryIO, Union, Tuple
from .binary_reader import BinaryReader


@dataclass
class HeightmapData:
    width: int = 0
    height: int = 0
    heights: List[int] = field(default_factory=list)

    @property
    def dimensions(self) -> Tuple[int, int]:
        return (self.width, self.height)

    def get_height(self, x: int, y: int) -> int:
        if 0 <= x < self.width and 0 <= y < self.height:
            return self.heights[y * self.width + x]
        raise IndexError(f"Heightmap coords ({x},{y}) out of bounds")


class HeightmapReader:
    """Reads .land heightmap files."""

    def __init__(self):
        self.data: Optional[HeightmapData] = None

    def load(self, source: Union[str, bytes, BinaryIO]) -> bool:
        reader = BinaryReader(source)
        reader.seek(0)

        _magic = reader.read_bytes(10)

        for _ in range(3):
            reader.read_u32()

        for _ in range(4):
            reader.read_u16()

        _code1 = reader.read_u32()
        _size  = reader.read_u16()
        pnumber = reader.read_u16()
        _unk   = reader.read_u16()

        points = pnumber
        total = points * points
        heights = reader.read_array("h", total)   # signed 16-bit

        self.data = HeightmapData(points, points, heights)
        return self.data is not None