# light_reader.py
"""Parser for .light texture archives."""
from dataclasses import dataclass, field
from typing import List, Optional, BinaryIO, Union
from .binary_reader import BinaryReader


@dataclass
class DayPartParams:
    x: float
    y: float
    z: float
    w: float


@dataclass
class LightData:
    tile_number: int = 256
    tiles_in_row: int = 8
    day_parts: int = 4
    format_enum: int = 21
    main_sub: int = 2
    main_qual: int = 90
    map_sub: int = 2
    map_qual: int = 90
    clipmap_sub: int = 2
    clipmap_qual: int = 90
    clipmap_stride1: int = 64
    clipmap_stride2: int = 64
    main_count: int = 256
    clipmap_count: int = 4096
    jpeg_data_start: int = 0
    params: List[DayPartParams] = field(default_factory=list)
    main_sizes: List[int] = field(default_factory=list)
    map_size: int = 0
    clipmap_sizes: List[int] = field(default_factory=list)


class LightReader:
    """Reads .light archives and extracts texture bytes."""

    MAGIC_SIZE = 11
    HEADER_SKIP_AFTER_MAGIC = 4 + 4 + 4

    def __init__(self):
        self.data: Optional[LightData] = None
        self._file: Optional[BinaryIO] = None
        self._owns_file = False

    def load(self, source: Union[str, bytes, BinaryIO]) -> bool:
        self._cleanup()
        if isinstance(source, str):
            self._file = open(source, "rb")
            self._owns_file = True
            reader = BinaryReader(self._file)
        else:
            reader = BinaryReader(source)

        self.data = self._parse(reader)
        return self.data is not None

    def close(self) -> None:
        self._cleanup()

    @staticmethod
    def calc_idx(x: int, y: int, day: int, grid: int) -> int:
        return day * (grid ** 2) + y * grid + x

    def get_texture_bytes(self, x: int, y: int, day: int) -> Optional[bytes]:
        if not self.data or not self._file:
            return None
        idx = self.calc_idx(x, y, day, self.data.tiles_in_row)
        if idx >= len(self.data.main_sizes):
            return None
        pos = self.data.jpeg_data_start
        for i in range(idx):
            pos += self.data.main_sizes[i]
        size = self.data.main_sizes[idx]
        old_pos = self._file.tell()
        try:
            self._file.seek(pos)
            return self._file.read(size)
        finally:
            self._file.seek(old_pos)

    def get_map_texture_bytes(self) -> Optional[bytes]:
        if not self.data or not self._file or self.data.map_size == 0:
            return None
        pos = self.data.jpeg_data_start
        for s in self.data.main_sizes:
            pos += s
        for s in self.data.clipmap_sizes:
            pos += s
        old_pos = self._file.tell()
        try:
            self._file.seek(pos)
            return self._file.read(self.data.map_size)
        finally:
            self._file.seek(old_pos)

    def get_clipmap_texture_bytes(self, index: int) -> Optional[bytes]:
        if not self.data or not self._file:
            return None
        if index >= len(self.data.clipmap_sizes):
            return None
        pos = self.data.jpeg_data_start
        for s in self.data.main_sizes:
            pos += s
        pos += self.data.map_size
        for i in range(index):
            pos += self.data.clipmap_sizes[i]
        size = self.data.clipmap_sizes[index]
        old_pos = self._file.tell()
        try:
            self._file.seek(pos)
            return self._file.read(size)
        finally:
            self._file.seek(old_pos)


    # light_reader.py  (append this method inside LightReader class)
    def get_all_main_tiles(self, day: int) -> List[bytes]:
        """Return a flat list of tile bytes for the given day part,
           ordered row‑major (0,0) .. (grid-1, grid-1)."""
        if not self.data or not self._file:
            return []
        grid = self.data.tiles_in_row
        tiles = []
        pos = self.data.jpeg_data_start
        # main tiles start at jpeg_data_start; we have already read all sizes,
        # so we can iterate.
        for idx in range(self.data.main_count):
            size = self.data.main_sizes[idx]
            old = self._file.tell()
            try:
                self._file.seek(pos)
                tiles.append(self._file.read(size))
            finally:
                self._file.seek(old)
            pos += size
        # Now extract only the tiles for the requested day part.
        # The flat list is day0_tiles, day1_tiles, ...
        day_offset = day * grid * grid
        return tiles[day_offset : day_offset + grid * grid]
        
    @property
    def main_qual(self) -> int:
        return self.data.main_qual if self.data else 90

    @property
    def main_sub(self) -> int:
        return self.data.main_sub if self.data else 2

    @property
    def tiles_in_row(self) -> int:
        return self.data.tiles_in_row if self.data else 8

    def _cleanup(self) -> None:
        if self._owns_file and self._file:
            self._file.close()
        self._file = None
        self._owns_file = False

    def _parse(self, r: BinaryReader) -> LightData:
        d = LightData()
        r.seek(self.MAGIC_SIZE)
        _unk = r.read_u32()
        d.tile_number = r.read_u32()
        d.tiles_in_row = r.read_u32()
        d.format_enum = r.read_u32()
        d.day_parts = r.read_u32()
        for _ in range(d.day_parts):
            x = r.read_f32()
            y = r.read_f32()
            z = r.read_f32()
            w = r.read_f32()
            d.params.append(DayPartParams(x, y, z, w))
        d.main_sub = r.read_u32()
        d.main_qual = r.read_u32()
        d.map_sub = r.read_u32()
        d.map_qual = r.read_u32()
        d.clipmap_sub = r.read_u32()
        d.clipmap_qual = r.read_u32()
        d.clipmap_stride1 = r.read_u32()
        d.clipmap_stride2 = r.read_u32()
        grid = d.tiles_in_row
        days = d.day_parts
        d.main_count = days * grid * grid
        print(d.main_count)
        eff = d.tile_number - 2
        tiles1 = (grid * eff) // d.clipmap_stride1 + 1
        tiles2 = (grid * eff) // d.clipmap_stride2 + 1
        d.clipmap_count = days * tiles1 * tiles2
        d.main_sizes = r.read_array("I", d.main_count)
        d.map_size = r.read_u32()
        d.clipmap_sizes = r.read_array("I", d.clipmap_count)
        d.jpeg_data_start = r.tell()
        
        print()
        return d