# Attribution

This package is a Forza Horizon 6 compatibility wrapper/importer around the
original `forza-painter` workflow.

## Original project

- `forza-painter` by AE / the_adawg
- Repository: https://github.com/forza-painter/forza-painter
- License: MIT

The original `forza-painter.exe`, settings, image generation workflow, and
original documentation remain from that project.

## FH6 memory-layout reference

The FH6 importer uses the `LiveryGroup + layer_table` discovery strategy that
was made public by the ForzaDesigner6 project.

- `ForzaDesigner6` by tokyubevoxelverse / contributors
- Repository: https://github.com/tokyubevoxelverse/ForzaDesigner6
- License: MIT

The relevant idea is:

- scan writable private FH6 memory for the active vinyl group's layer count
- validate the candidate `LiveryGroup`
- read its `layer_table`
- write transforms/colors through the actual layer pointers

## This FH6-ready wrapper

Added files:

- `forza-painter-fh6-ready.exe`
- `tools/Fh6PainterLauncher.cs`
- `tools/Fh6ImportLayerTable.exe`
- `tools/Fh6ImportLayerTable.cs`
- `README_FH6_READY.md`

These files keep the original drag-and-drop workflow:

- image file -> original `forza-painter.exe` generator
- JSON file -> FH6 layer-table importer

## Disclaimer

This tool writes to the memory of a running Forza Horizon 6 process. Use it at
your own risk. It is not affiliated with, endorsed by, or supported by Microsoft,
Xbox, Turn 10 Studios, Playground Games, Forza, the original `forza-painter`
author, or the ForzaDesigner6 project.
