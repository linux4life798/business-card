# Business card project

Read [README.md](README.md) for the project overview and file locations.

- Keep changes scoped to the request and preserve unrelated work.
- Respect library-only edits. Update the PCB's embedded footprints from the library only when propagation is intended, then save before rendering.
- Keep the README minimal and consistent with the saved schematic and PCB. Update affected descriptions and links alongside design changes.
- Keep both PNGs and `render-readme.py` together in the flat, root-level `docs/` directory. Regenerate both images from `business-card.kicad_pcb` after visible design changes.
- Always render exposed copper as gold, using the script's temporary ENIG override. Preserve the main PCB's fabrication settings, geometry, solder mask, and silkscreen; do not retouch renders.
- Inspect both PNGs for clipping, orientation, missing models, and the gold finish. Check the README preview and links, and label the images as KiCad renders.

Regenerate all README previews (front/back PNGs and schematic SVG/PDF) from the saved design, running from the repository root with Python 3, KiCad 10, and its standard 3D model libraries installed:

```sh
python3 docs/render-readme.py
```

Use `--only schematic` to refresh just the SVG and PDF, or `--only pcb` for the two 3D renders.
