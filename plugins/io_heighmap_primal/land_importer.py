# land_importer.py
"""Blender mesh and material generation utilities (optimized)."""
import bpy


def create_mesh(width, height, heights, scale=0.02, name="Terrain"):
    """Create a mesh from a height array – fast implementation."""
    mesh = bpy.data.meshes.new(f"{name}_Mesh")

    # Build vertex coordinates as a flat list
    verts = [
        (x, y, heights[y * width + x] * scale)
        for y in range(height)
        for x in range(width)
    ]

    # Build faces using a single list comprehension
    faces = [
        (y * width + x, y * width + x + 1,
         (y + 1) * width + x + 1, (y + 1) * width + x)
        for y in range(height - 1)
        for x in range(width - 1)
    ]

    mesh.from_pydata(verts, [], faces)
    mesh.update()

    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    return obj


def apply_uv(mesh, w, h):
    """Apply UV coordinates – unchanged."""
    uv_layer = mesh.uv_layers.new(name="UV").data
    for loop in mesh.loops:
        v = mesh.vertices[loop.vertex_index]
        u = v.co[0] / max(w - 1, 1)
        v_coord = 1.0 - v.co[1] / max(h - 1, 1)
        uv_layer[loop.index].uv = (u, v_coord)


def _create_mat(img, mat_name):
    """Create a simple material with a texture – unchanged."""
    mat = bpy.data.materials.new(mat_name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    tex = nodes.new("ShaderNodeTexImage")
    tex.image = img
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    out = nodes.new("ShaderNodeOutputMaterial")

    links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    return mat


def apply_single_material(obj, img, base_name):
    obj.data.materials.clear()
    if img:
        mat = _create_mat(img, f"{base_name}_{img.name}")
        obj.data.materials.append(mat)
    else:
        mat = bpy.data.materials.new(f"{base_name}_Fallback")
        mat.diffuse_color = (0.5, 0.5, 0.5, 1.0)
        obj.data.materials.append(mat)


def apply_day_materials(obj, day_images, base_name):
    obj.data.materials.clear()
    names = ["Dawn", "Day", "Dusk", "Night"]
    for i, img in enumerate(day_images):
        if img:
            mat = _create_mat(img, f"{base_name}_{names[i]}")
            obj.data.materials.append(mat)
        else:
            mat = bpy.data.materials.new(f"{base_name}_{names[i]}_Fallback")
            mat.diffuse_color = (0.5, 0.5, 0.5, 1.0)
            obj.data.materials.append(mat)
    obj.active_material_index = 1  # Default to Day


def assign_tile_materials(obj, tile_images, tiles_in_row, tile_size):
    """Assign per‑face materials based on tile index – unchanged."""
    mesh = obj.data
    mesh.materials.clear()

    mats = []
    for idx, img in enumerate(tile_images):
        if img is None:
            mat = bpy.data.materials.new(f"Tile_{idx}_fallback")
            mat.diffuse_color = (0.5, 0.5, 0.5, 1.0)
            mesh.materials.append(mat)
            mats.append(mat)
            continue
        mat = bpy.data.materials.new(f"Tile_{idx}")
        mat.use_nodes = True
        nodes = mat.node_tree.nodes
        links = mat.node_tree.links
        nodes.clear()
        tex = nodes.new("ShaderNodeTexImage")
        tex.image = img
        bsdf = nodes.new("ShaderNodeBsdfPrincipled")
        out = nodes.new("ShaderNodeOutputMaterial")
        links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
        links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
        mesh.materials.append(mat)
        mats.append(mat)

    for face in mesh.polygons:
        v0 = mesh.vertices[face.vertices[0]].co
        v1 = mesh.vertices[face.vertices[1]].co
        v2 = mesh.vertices[face.vertices[2]].co
        v3 = mesh.vertices[face.vertices[3]].co
        cx = (v0.x + v1.x + v2.x + v3.x) / 4.0
        cy = (v0.y + v1.y + v2.y + v3.y) / 4.0
        tx = int(cx // tile_size)
        ty = int(cy // tile_size)
        tile_index = ty * tiles_in_row + tx
        face.material_index = min(tile_index, len(mats) - 1)