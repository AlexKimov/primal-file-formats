# binary_writer.py
import struct
from typing import List, Union

class BinaryWriter:
    """Wraps a bytearray with convenient write methods (little‑endian by default)."""

    def __init__(self, endian: str = "<"):
        self._prefix = endian
        self._buffer = bytearray()
        self._pos = 0

    def _write(self, data: bytes) -> None:
        """Write raw bytes at the current position and advance."""
        self._buffer[self._pos : self._pos] = data
        self._pos += len(data)

    def _pack(self, fmt: str, value) -> None:
        full_fmt = f"{self._prefix}{fmt}"
        self._write(struct.pack(full_fmt, value))

    # Convenience methods
    def write_u8(self, value: int) -> None:
        self._pack("B", value)

    def write_i16(self, value: int) -> None:
        self._pack("h", value)

    def write_u16(self, value: int) -> None:
        self._pack("H", value)

    def write_u32(self, value: int) -> None:
        self._pack("I", value)

    def write_f32(self, value: float) -> None:
        self._pack("f", value)

    def write_bytes(self, data: bytes) -> None:
        self._write(data)

    def write_array(self, fmt: str, values: List[Union[int, float]]) -> None:
        """Write a packed array of values (e.g. 'h' for int16, 'I' for uint32)."""
        full_fmt = f"{self._prefix}{fmt}{len(values)}"
        self._write(struct.pack(full_fmt, *values))

    def seek(self, offset: int, whence: int = 0) -> None:
        if whence == 0:
            self._pos = offset
        elif whence == 1:
            self._pos += offset
        elif whence == 2:
            self._pos = len(self._buffer) + offset
        else:
            raise ValueError("Invalid whence")

    def skip(self, n: int) -> None:
        self._pos += n

    def tell(self) -> int:
        return self._pos

    def to_bytes(self) -> bytes:
        """Return the final bytes of the stream."""
        return bytes(self._buffer[: self._pos])

    def __len__(self):
        return len(self._buffer)

    def clear(self) -> None:
        self._buffer = bytearray()
        self._pos = 0