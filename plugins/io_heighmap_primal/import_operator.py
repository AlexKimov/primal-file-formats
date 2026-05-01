# import_operator.py
"""Blender import operator for Primal .land/.light files."""
import bpy
import os
import tempfile
from bpy.props import (
    StringProperty, FloatProperty, IntProperty, BoolProperty, EnumProperty
)
from bpy_extras.io_utils import ImportHelper

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

from . import terrain_reader
from . import jpeg_processor
from . import land_importer
from . import ui


class ImportPrimal(bpy.types.Operator, ImportHelper):
    bl_idname = "import_mesh.primal"
    bl_label = "Import .land/.light"
    filter_glob: StringProperty(default="*.land;", options={"HIDDEN"})

    height_scale: FloatProperty(default=0.02, min=0.001, max=0.2)
    cell_size: IntProperty(default=6, min=0, max=100)
    load_textures: BoolProperty(default=True)
    load_mode: EnumProperty(
        name="Load Mode",
        items=[
            ("ALL", "All Day Parts", "Load all four day variants"),
            ("SINGLE", "Single Part", "Load only the selected day part"),
        ],
        default="SINGLE"
    )
    day_part: EnumProperty(
        items=[
            ("0", "Dawn", ""), ("1", "Day", ""),
            ("2", "Dusk", ""), ("3", "Night", ""),
        ],
        default="1",
    )
    texture_type: EnumProperty(
        name="Texture Layout",
        items=[
            ("ATLAS", "Texture Atlas", "Stitch all tiles into one large image (requires Pillow)"),
            ("SEPARATE", "Separate Tiles", "Load each tile individually"),
        ],
        default="ATLAS"
    )
    export_textures: BoolProperty(
        name="Export textures to folder",
        default=False
    )
    extract_only: BoolProperty(
        name="Extract only (no mesh)",
        default=False
    )

    def draw(self, context):
        ui.draw_import_ui(self.layout, self)

    def _make_proc(self):
        return jpeg_processor.JpegProcessor()

    def _save_tile(self, proc, raw, quality, sub, save_path):
        return proc.process_to_file(raw, save_path, quality, sub)

    def _load_image(self, path, name=None):
        if not path or not os.path.exists(path):
            return None
        img = bpy.data.images.load(path, check_existing=True)
        if name and img:
            img.name = name
        return img

    def _stitch_atlas(self, tile_paths, atlas_path, tile_size, grid, quality):
        if not PIL_AVAILABLE:
            self.report({"ERROR"}, "Pillow is required for atlas mode.")
            return None
        images = []
        for p in tile_paths:
            try:
                images.append(Image.open(p))
            except Exception as e:
                print(f"[ImportPrimal] Error opening tile {p}: {e}")
                return None
        atlas_w = tile_size * grid
        atlas = Image.new("RGB", (atlas_w, atlas_w))
        for idx, img in enumerate(images):
            col = idx % grid
            row = idx // grid
            atlas.paste(img, (col * tile_size, row * tile_size))
        os.makedirs(os.path.dirname(atlas_path), exist_ok=True)
        atlas.save(atlas_path, "JPEG", quality=quality)
        return atlas_path

    def execute(self, context):
        if not os.path.exists(self.filepath):
            self.report({"ERROR"}, "File not found")
            return {"CANCELLED"}

        base = os.path.splitext(self.filepath)[0]
        light_path = base + ".light"
        if not os.path.exists(light_path):
            light_path = None

        export_dir = None
        if light_path and (self.export_textures or self.extract_only):
            export_dir = os.path.join(os.path.dirname(light_path), "textures")

        if self.extract_only:
            if not light_path:
                self.report({"ERROR"}, "Extract only requires a .light file")
                return {"CANCELLED"}
            proc = self._make_proc()
            rd = terrain_reader.LightReader()
            if not rd.load(light_path):
                self.report({"ERROR"}, "Failed to read .light")
                return {"CANCELLED"}
            grid = rd.tiles_in_row
            tile_size = rd.data.tile_number
            quality = rd.data.main_qual
            sub = rd.data.main_sub
            saved = 0
            for day in range(rd.data.day_parts):
                tiles = rd.get_all_main_tiles(day)
                if not tiles:
                    continue
                for idx, raw in enumerate(tiles):
                    tx = idx % grid
                    ty = idx // grid
                    path = os.path.join(export_dir, f"tile_day{day}_{tx}_{ty}.jpg")
                    if self._save_tile(proc, raw, quality, sub, path):
                        saved += 1
            rd.close()
            self.report({"INFO"}, f"Extracted {saved} tiles to {export_dir}")
            return {"FINISHED"}

        with terrain_reader.TerrainReader() as rd:
            rd.load_heightmap(self.filepath)
            hm = rd.heightmap.data
            obj = land_importer.create_mesh(
                hm.width, hm.height, hm.heights, self.height_scale
            )
            land_importer.apply_uv(obj.data, hm.width, hm.height)

            if light_path:
                rd.load_light(light_path)
            else:
                print("[ImportPrimal] No .light file found")

            if self.load_textures and light_path and rd.light:
                proc = self._make_proc()
                base_name = os.path.basename(light_path)
                grid = rd.light.tiles_in_row
                tile_size = rd.light.data.tile_number
                quality = rd.light.main_qual
                sub = rd.light.main_sub

                if self.load_mode == 'ALL':
                    day_images = []
                    for day in range(4):
                        tiles = rd.light.get_all_main_tiles(day)
                        if tiles is None:
                            tiles = []
                        if not tiles:
                            day_images.append(None)
                            continue
                        if self.texture_type == 'ATLAS':
                            atlas_img = self._load_atlas_for_day(
                                tiles, proc, quality, sub, grid, tile_size,
                                day, base_name, export_dir
                            )
                            day_images.append(atlas_img)
                        else:
                            tile_imgs = self._load_separate_for_day(
                                tiles, proc, quality, sub, grid, tile_size,
                                day, base_name, export_dir
                            )
                            day_images.append(tile_imgs[0] if tile_imgs else None)
                    land_importer.apply_day_materials(obj, day_images, base_name)
                else:
                    day = int(self.day_part)
                    tiles = rd.light.get_all_main_tiles(day)
                    if tiles is None:
                        tiles = []
                    if not tiles:
                        self.report({"WARNING"}, "No tiles found for selected day")
                    else:
                        if self.texture_type == 'ATLAS':
                            atlas_img = self._load_atlas_for_day(
                                tiles, proc, quality, sub, grid, tile_size,
                                day, base_name, export_dir
                            )
                            land_importer.apply_single_material(obj, atlas_img, base_name)
                        else:
                            tile_images = self._load_separate_for_day(
                                tiles, proc, quality, sub, grid, tile_size,
                                day, base_name, export_dir
                            )
                            land_importer.assign_tile_materials(obj, tile_images, grid, tile_size)
                    obj.primal_day_part = str(day)

        context.view_layer.objects.active = obj
        obj.select_set(True)
        self.report({"INFO"}, "Import complete")
        return {"FINISHED"}

    def _load_atlas_for_day(self, tiles, proc, quality, sub, grid, tile_size,
                            day, base_name, export_dir):
        tile_paths = []
        for idx, raw in enumerate(tiles):
            tx = idx % grid
            ty = idx // grid
            path = None
            if export_dir:
                path = os.path.join(export_dir, f"tile_day{day}_{tx}_{ty}.jpg")
            saved = self._save_tile(proc, raw, quality, sub, path)
            if saved:
                tile_paths.append(saved)
        if not tile_paths:
            return None

        print(f"[ImportPrimal] Stitching {len(tile_paths)} tiles into atlas for day {day}")
        atlas_path = os.path.join(export_dir if export_dir else tempfile.gettempdir(),
                                  f"{base_name}_day{day}_atlas.jpg")
        atlas_path = self._stitch_atlas(tile_paths, atlas_path, tile_size, grid, quality)
        if not atlas_path:
            print("[ImportPrimal] Atlas stitching FAILED")
            return None
        print(f"[ImportPrimal] Atlas saved to: {atlas_path}")

        img = self._load_image(atlas_path, f"{base_name}_day{day}_atlas")
        if img is None:
            print("[ImportPrimal] FAILED to load atlas image into Blender")
        else:
            print(f"[ImportPrimal] Atlas image loaded: {img.name} ({img.size[0]}x{img.size[1]})")

        if not export_dir:
            for p in tile_paths:
                if os.path.exists(p): os.unlink(p)
            if os.path.exists(atlas_path): os.unlink(atlas_path)

        return img

    def _load_separate_for_day(self, tiles, proc, quality, sub, grid, tile_size,
                               day, base_name, export_dir):
        images = []
        for idx, raw in enumerate(tiles):
            tx = idx % grid
            ty = idx // grid
            path = None
            if export_dir:
                path = os.path.join(export_dir, f"tile_day{day}_{tx}_{ty}.jpg")
            saved = self._save_tile(proc, raw, quality, sub, path)
            if saved:
                img = self._load_image(saved, f"{base_name}_day{day}_tile_{tx}_{ty}")
                images.append(img)
                if not export_dir and os.path.exists(saved):
                    os.unlink(saved)
            else:
                images.append(None)
        return images


def menu_func(self, context):
    self.layout.operator(ImportPrimal.bl_idname, text="Primal .land/.light")