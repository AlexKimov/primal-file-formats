# primal-file-formats

File formats and tools for games by Primal Software
## Formats
| № | Format/Ext  | Template (010 Editor) |  Description   |
| :-- | :------- | :-- |  :-- | 
|  **1**  | MESH | [MESH.bt](https://github.com/AlexKimov/primal-file-formats/blob/master/templates/010editor/MESH.bt)  | models | 
|  **2**  | ANM | [ANM.bt](https://github.com/AlexKimov/primal-file-formats/blob/master/templates/010editor/ANM.bt)  | animations | 

## Tools

#### QuickBMS 

| № | .bat file | Script  | Description   |
| :-- | :------- | :-------  | :-- |
|  **1**  | [run_res.bat](https://github.com/AlexKimov/primal-file-formats/blob/master/scripts/run_res.bat) | [idragon_unpack_res.bms](https://github.com/AlexKimov/primal-file-formats/blob/master/scripts/idragon_unpack_res.bms) | unpack resource files |

#### Blender

| № | Plugin | Description   |
| :-- | :------- | :-------  | 
|  **1**  | [_init__.py](https://github.com/AlexKimov/primal-file-formats/blob/master/plugins/blender/io_scene_idragon_mesh/__init__.py)  | Plugin to open mesh files |


    How to:
    1. Install Blender (~3.3).
    2. Go to Preferencies - Add-ons section - Testing. Check plugin to activate.
    3. Go to menu File - Import - "Plugin" and choose .mesh file to import.
