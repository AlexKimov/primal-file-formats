# Описание

Форматы файлов и инструменты для игр Primal Software.

## Форматы

| № | Format/Ext  | Template (010 Editor) |  Description   |
| :-- | :------- | :-- |  :-- | 
|  **1**  | MESH | [MESH.bt](https://github.com/AlexKimov/primal-file-formats/blob/master/templates/010editor/MESH.bt)  | трехмерные модели | 
|  **2**  | ANM | [ANM.bt](https://github.com/AlexKimov/primal-file-formats/blob/master/templates/010editor/ANM.bt)  | анимации для трехмерных моделей | 

## Инструменты

#### Noesis

| № | Плагин | Описание   |
| :-- | :------- | :-------  | 
|  **1**  | [fmt_idragon_msh.py](plugins/noesis/fmt_idragon_msh.py)  | Просмотр файлов моделей mesh игры Глаз Дракона (2003) |

    Как использовать Noesis плагины
    1. Скачать Noesis https://richwhitehouse.com/index.php?content=inc_projects.php&showproject=91 .
    2. Скопировать скрипт в папку ПапкасNoesis/plugins/python.
    3. Открыть Noesis.
    4. Открыть файл через File-Open.

***

# primal-file-formats

File formats and tools for games by Primal Software.

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

#### Noesis

| № | Plugin | Description   |
| :-- | :------- | :-------  | 
|  **1**  | [fmt_idragon_msh.py](plugins/noesis/fmt_idragon_msh.py)  | Plugin to open mesh files |

![Dragon](dragon.png)
