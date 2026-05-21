# Forza Painter FH6 Ready

Use `forza-painter-fh6-ready.exe` for the normal drag-and-drop workflow.

## Generate JSON

Drag a `.png`, `.jpg`, or other image onto:

```text
forza-painter-fh6-ready.exe
```

The launcher forwards images to the original `forza-painter.exe`, so image
generation works like the original tool.

Before generation starts, the launcher asks how many layers to generate. It
then updates all generator profiles to that `stopAt` value for the run.

FH6 surface limits:

- Front bumper: 1000 layers.
- Rear bumper: 1000 layers.
- Left side, right side, and top: up to 3000 layers each.

## Import JSON into FH6

1. Open Forza Horizon 6.
2. Open the vinyl group editor.
3. Load a fresh template with enough circle/sphere layers, usually 2000.
4. Ungroup it if the template loads grouped.
5. Drag the generated `.json` onto:

```text
forza-painter-fh6-ready.exe
```

The launcher forwards JSON files to `tools\Fh6ImportLayerTable.exe`, which uses
the FH6 `LiveryGroup` layer table instead of the old FH5 descriptor path.

Before import starts, the launcher asks how many layers the active FH6 template
has. Press Enter to accept the detected recommendation, or type a value such as
`1500`, `2000`, or `3000`.

For bumper vinyls, enter `1000` and use a 1000-layer template. For side/top
vinyls, use any matching template up to 3000 layers.

## Scan/cache behavior

The first import for an open FH6/editor session can take a few minutes because
the importer has to find the active layer table in memory.

Further imports are fast only while the same FH6 process and the same active
vinyl group remain open. If you save, leave the editor, reload the vinyl group,
or restart FH6, the layer pointers can move and the importer must scan again.

During scanning, nothing is written until you see `LiveryGroup found` and then
`written ...`.

## Folder layout

- `forza-painter.exe`: original generator.
- `forza-painter-fh6-ready.exe`: drag-and-drop launcher for FH6 workflow.
- `tools\Fh6ImportLayerTable.exe`: FH6 JSON importer.
- `settings\`: generator profiles. The launcher updates `stopAt` before image
  generation based on the layer count you enter.
- `README_ORIGINAL_FORZA_PAINTER.md`: original ForzaPainter documentation.
