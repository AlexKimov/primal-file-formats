# jpeg_processor.py
"""JPEG reconstruction for Primal .light textures.
   Replaces missing DQT/DHT tables (IJL streams) and re‑encodes at archive quality.
   Always produces valid JPEG bytes or returns None."""

import struct
import os
import tempfile
from typing import Optional

from .jpeg_tables import (
    build_full_header,
    extract_scan_data,
    reencode_with_ijl
)

class JpegProcessor:
    """Processes Primal IJL streams into complete JPEGs."""
    HAS_LIB = True

    def process(self, raw_data: bytes, quality: int = 90,
                subsampling: int = 2) -> Optional[bytes]:
        if not raw_data:
            return None

        # Determine dimensions from SOF0
        sof0_pos = raw_data.find(b'\xff\xc0')
        if sof0_pos != -1:
            height = struct.unpack('>H', raw_data[sof0_pos+5:sof0_pos+7])[0]
            width  = struct.unpack('>H', raw_data[sof0_pos+7:sof0_pos+9])[0]
        else:
            height = width = 256

        # Extract scan data (handles both raw and partial streams)
        scan = extract_scan_data(raw_data)
        header = build_full_header(height, width)
        rebuilt = header + scan + b'\xff\xd9'
        return reencode_with_ijl(rebuilt, quality)

    def process_to_file(self, raw_data: bytes, output_path: Optional[str],
                        quality: int = 90, subsampling: int = 2) -> Optional[str]:
        jpeg_bytes = self.process(raw_data, quality, subsampling)
        if not jpeg_bytes:
            return None
        if output_path:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            with open(output_path, 'wb') as f:
                f.write(jpeg_bytes)
            return output_path
        else:
            tmp = tempfile.NamedTemporaryFile(suffix='.jpg', delete=False)
            tmp.write(jpeg_bytes)
            tmp.close()
            return tmp.name