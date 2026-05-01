import io
import struct
from typing import BinaryIO, Union, List


class BinaryReader:
    """Wraps a binary stream with convenient read methods."""

    def __init__(
        self,
        source: Union[str, bytes, BinaryIO],
        endian: str = "<"
    ):
        self._prefix = endian
        self._owns_stream = False
        self._stream: BinaryIO

        if isinstance(source, str):
            self._stream = open(source, "rb")
            self._owns_stream = True
        elif isinstance(source, bytes):
            self._stream = io.BytesIO(source)
        else:
            self._stream = source

    def __enter__(self) -> "BinaryReader":
        return self

    def __exit__(self, *args) -> None:
        self.close()

    def close(self) -> None:
        if self._owns_stream:
            self._stream.close()
            self._owns_stream = False

    def _read_raw(self, size: int) -> bytes:
        chunk = self._stream.read(size)
        if len(chunk) < size:
            raise EOFError(f"Expected {size} bytes")
        return chunk

    def _unpack(self, fmt: str) -> Union[int, float]:
        full_fmt = f"{self._prefix}{fmt}"
        return struct.unpack(
            full_fmt, self._read_raw(struct.calcsize(fmt))
        )[0]

    def read_u8(self) -> int:
        return self._unpack("B")

    def read_i16(self) -> int:
        return self._unpack("h")
        
    def read_u16(self) -> int:
        return self._unpack("H")        

    def read_u32(self) -> int:
        return self._unpack("I")

    def read_f32(self) -> float:
        return self._unpack("f")

    def read_bytes(self, n: int) -> bytes:
        return self._read_raw(n)

    def read_array(self, fmt: str, count: int) -> List[Union[int, float]]:
        size = struct.calcsize(fmt)
        full_fmt = f"{self._prefix}{fmt * count}"
        return list(
            struct.unpack(full_fmt, self._read_raw(size * count))
        )

    def seek(self, offset: int, whence: int = 0) -> int:
        return self._stream.seek(offset, whence)

    def tell(self) -> int:
        return self._stream.tell()

    def skip(self, n: int) -> int:
        return self.seek(n, 1)