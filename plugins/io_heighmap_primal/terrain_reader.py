"""Unified interface for terrain and light data."""
from typing import Union, BinaryIO, Optional
from .light_reader import LightReader
from .heightmap_reader import HeightmapReader


class TerrainReader:
    """Convenience wrapper that manages light and heightmap readers."""

    def __init__(self):
        self.light = LightReader()
        self.heightmap = HeightmapReader()

    def __enter__(self) -> "TerrainReader":
        return self

    def __exit__(self, *args) -> None:
        self.close()

    def load_light(self, source: Union[str, bytes, BinaryIO]) -> bool:
        return self.light.load(source)

    def load_heightmap(
        self, source: Union[str, bytes, BinaryIO]
    ) -> bool:
        return self.heightmap.load(source)

    def get_texture_bytes(
        self, x: int, y: int, day: int
    ) -> Optional[bytes]:
        return self.light.get_texture_bytes(x, y, day)

    def close(self) -> None:
        self.light.close()