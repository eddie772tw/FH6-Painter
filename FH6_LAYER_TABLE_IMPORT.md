# FH6 layer-table importer

This is the current FH6 path for ForzaPainter JSON imports. It is based on the
working ForzaDesigner6 approach:

- scan writable private FH6 memory for the active `LiveryGroup`
- read the `layer_table` pointer from that group
- write each layer through the real layer pointer table

This replaces the older session-specific address mapping experiments.

## Safety

Use at your own risk. This writes to the memory of the running FH6 process.
Do not move, edit, add, delete, or select shapes while an import is running.

The importer validates candidates before writing. If it cannot find a confident
layer table, it exits without writing.

## In Forza Horizon 6

1. Open the Vinyl Group editor.
2. Load a fresh template with enough sphere/circle layers.
3. Ungroup the template if it loads grouped.
4. Leave the layer list/editor open and do not touch it during import.

## Dry run

This scans and validates only; it does not write:

```powershell
.\tools\Fh6ImportLayerTable.exe .\your-file.json --layers=3000 --dry-run
```

Expected result: `LiveryGroup found. Valid layer pointers=3000` plus a preview
of the first writes.

## Import

```powershell
.\tools\Fh6ImportLayerTable.exe .\your-file.json --layers=3000
```

Options:

- `--layers=1500` or `--layers=3000` sets the current template layer count.
- `--reverse` reverses JSON-to-layer order if the image stacks upside down.
- `--scale-div=63` controls shape scale conversion. `63` matches the
  ForzaDesigner6 ellipse convention; older experiments used `100`.
- `--coord-scale=1` applies an extra multiplier to X/Y positions.
- `--include-header` writes the transparent ForzaPainter canvas header shape.
  Normally leave this off.

## Notes

ForzaPainter JSONs often contain a transparent first shape with
`type=1`, `data=[0,0,width,height]`, and alpha `0`. This importer treats that
as canvas metadata and skips it by default.
