import argparse
import os
import struct
import sys
import shutil
from pathlib import Path

# Configuration
UINT32_FORMAT = '<I' 
UINT32_SIZE = 4

def read_uint32(f):
    data = f.read(UINT32_SIZE)
    if len(data) < UINT32_SIZE:
        raise EOFError("Unexpected end of file while reading uint32")
    return struct.unpack(UINT32_FORMAT, data)[0]

def write_uint32(f, value):
    f.write(struct.pack(UINT32_FORMAT, value))

def unpack_archive(res_path, output_base_dir):
    """
    Unpacks a single .res file into a subdirectory within output_base_dir.
    Subdirectory name matches the .res filename (stem).
    """
    if not res_path.exists():
        print(f"Error: File not found: {res_path}")
        return

    print(f"Unpacking: {res_path.name}")
    
    # Create output folder named after the res file (without extension)
    folder_name = res_path.stem
    dest_folder = output_base_dir / folder_name
    dest_folder.mkdir(parents=True, exist_ok=True)

    try:
        with open(res_path, 'rb') as f:
            # get FILES long
            file_count = read_uint32(f)
            # Read File Table
            for i in range(file_count):
                name_len = read_uint32(f)
                name_bytes = f.read(name_len)
                name = name_bytes.decode('ascii')
                offset = read_uint32(f)
                size = read_uint32(f)
                
                cur_offs = f.tell()
                f.seek(offset, 0)
                
                file_path = dest_folder / name
                file_path.parent.mkdir(parents=True, exist_ok=True)
                    
                with open(file_path, 'wb') as out_f:                   
                    data = f.read(size)
                    out_f.write(data)    
                f.seek(cur_offs)
            
            print(f"  Successfully extracted {file_count} files to '{dest_folder}'")

    except Exception as e:
        print(f"  [ERROR] Failed to unpack {res_path.name}: {e}")

def pad_data_by_16(data_length):
    return 0 if data_length % 16 == 0 else (16 - data_length % 16)

def pack_directory(source_dir, output_res_path):
    """
    Packs all files in source_dir into a single .res file at output_res_path.
    """
    if not source_dir.is_dir():
        print(f"Error: Source path is not a directory: {source_dir}")
        return

    print(f"Packing: {source_dir.name} -> {output_res_path.name}")

    files_to_pack = []
    
    # Walk through the directory
    current_offset = 4
    for root, _, files in os.walk(source_dir):
        for filename in files:
            full_path = Path(root) / filename
            rel_path = full_path.relative_to(source_dir)
            
            # Normalize separators to backslash
            rel_path_str = str(rel_path).replace('/', '\\')
            
            size = full_path.stat().st_size
            padding = pad_data_by_16(size)
            files_to_pack.append({
                'path': full_path,
                'name': rel_path_str,
                'size': full_path.stat().st_size,
                'padding': padding
            })
            current_offset += 12 + len(rel_path_str) 
    
    padding = pad_data_by_16(current_offset)
    current_offset += padding
    
    print(f"  Found {len(files_to_pack)} files.")

    try:
        with open(output_res_path, 'wb') as out_f:
            # 1. Calculate Header Size

            # 2. Write Header (File Count)
            write_uint32(out_f, len(files_to_pack))

            # 3. Write Table
            current_data_ptr = current_offset
            for entry in files_to_pack:
                # print(entry['name'])
                name_bytes = entry['name'].encode('ascii')
                
                write_uint32(out_f, len(name_bytes)) # length
                out_f.write(name_bytes)              # NAME
                write_uint32(out_f, current_data_ptr)# OFFSET
                write_uint32(out_f, entry['size'])   # SIZE
                
                current_data_ptr += entry['size'] + entry['padding']
            
            out_f.write(bytes(padding))
            
            # 4. Write File Data
            for index, entry in enumerate(files_to_pack):
                with open(entry['path'], 'rb') as src_f:
                    shutil.copyfileobj(src_f, out_f)
                    if len(files_to_pack) - 1 != index:
                        out_f.write(bytes(entry['padding']))

            print(f"  Successfully packed {len(files_to_pack)} files ({current_data_ptr} bytes total)")

    except Exception as e:
        print(f"  [ERROR] Failed to pack {source_dir.name}: {e}")

def main():
    parser = argparse.ArgumentParser(description="I of the Dragon .res Archive Tool")
    subparsers = parser.add_subparsers(dest='command', help='Command to run')

    # --- UNPACK COMMAND ---
    # Input: Directory containing .res files
    # Output: Directory where extracted folders will be created
    parser_unpack = subparsers.add_parser('unpack', help='Unpack .res files from a directory')
    parser_unpack.add_argument('-i', '--input', required=True, type=Path, help='Input directory containing .res files')
    parser_unpack.add_argument('-o', '--output', required=True, type=Path, help='Output directory for extracted folders')

    # --- PACK COMMAND ---
    # Input: Directory containing folders (unpacked archives)
    # Output: Directory where .res files will be created
    parser_pack = subparsers.add_parser('pack', help='Pack folders into .res files')
    parser_pack.add_argument('-i', '--input', required=True, type=Path, help='Input directory containing subfolders to pack')
    parser_pack.add_argument('-o', '--output', required=True, type=Path, help='Output directory for generated .res files')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    if args.command == 'unpack':
        input_dir = args.input
        output_dir = args.output
        
        if not input_dir.is_dir():
            print(f"Error: Input must be a directory: {input_dir}")
            sys.exit(1)
        
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Find all .res files in input directory
        res_files = list(input_dir.glob('*.res'))
        
        if not res_files:
            print(f"No .res files found in {input_dir}")
            sys.exit(0)

        for res_file in res_files:
            unpack_archive(res_file, output_dir)

    elif args.command == 'pack':
        input_dir = args.input
        output_dir = args.output
        
        if not input_dir.is_dir():
            print(f"Error: Input must be a directory: {input_dir}")
            sys.exit(1)
        
        output_dir.mkdir(parents=True, exist_ok=True)

        # Find all immediate subdirectories in the input folder
        folders_to_pack = [d for d in input_dir.iterdir() if d.is_dir()]
        
        if not folders_to_pack:
            print(f"No subdirectories found in {input_dir} to pack.")
            sys.exit(0)

        for folder in folders_to_pack:
            output_file = output_dir / f"{folder.name}.res"
            pack_directory(folder, output_file)

if __name__ == '__main__':
    main()