# Forza Painter FH6 Ready v0.1.0

Initial public-ready build for Forza Horizon 6.

## What works

- Drag an image onto `forza-painter-fh6-ready.exe` to generate a ForzaPainter
  JSON using the original generator.
- Drag a generated JSON onto `forza-painter-fh6-ready.exe` to import into FH6.
- The launcher asks how many layers to use before generation/import.
- Supports common FH6 surface limits:
  - front/rear bumper: 1000 layers
  - left/right/top: up to 3000 layers
- Uses FH6 `LiveryGroup + layer_table` discovery instead of the old FH5
  descriptor path.
- Skips the transparent ForzaPainter canvas header shape automatically.
- Shows scan progress and refuses to write when no confident layer table is
  found.

## Known behavior

- The first import in a FH6/editor session can take a few minutes while memory
  is scanned.
- Later imports are fast only while the same FH6 process and the same active
  vinyl group remain open.
- Saving, leaving the editor, reloading a vinyl group, or restarting FH6 can
  move layer pointers, causing a full scan again.
- Do not edit, add, remove, move, or select layers while an import is running.

## Suggested use

- Bumpers: generate/import with 1000 layers.
- Side/top: use 1500-2000 for normal work, 3000 only for heavy detail.

## Credits

See `ATTRIBUTION_FH6_READY.md`.
