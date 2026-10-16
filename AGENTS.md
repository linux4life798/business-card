# Business card project

Read [README.md](README.md) for the project overview and file locations.

- Keep the project usable entirely through KiCad's GUI, including personalization, inspection, and export. Bundle portable custom libraries/assets and make steps clear to beginners; Python, contact files, and Actions are optional conveniences.
- Keep Python small, readable, and focused, with minimal options and outputs. Use modern parameter and return annotations, built-in collection types, and `|` unions; avoid clever abstractions and compressed code.
- Keep changes scoped to the request and preserve unrelated work.
- Respect library-only edits. Update the PCB's embedded footprints from the library only when propagation is intended, then save before rendering.
- Make the README a concise welcome: what the project is, previews, and how to get started. Let users learn progressively: explain mechanisms as they become relevant, with links to deeper explanations. Keep design rationale, calculations, and history in separate notes so users can explore without needing to understand everything upfront.
- Keep README descriptions and links consistent with the saved schematic and PCB, updating them alongside design changes.
- Keep both PNGs and `render-readme.py` together in the flat, root-level `docs/` directory. Regenerate both images from `business-card.kicad_pcb` after visible design changes.
- Always render exposed copper as gold, using the script's temporary ENIG override. Preserve the main PCB's fabrication settings, geometry, solder mask, and silkscreen; do not retouch renders.
- Inspect both PNGs for clipping, orientation, missing models, and the gold finish. Check the README preview and links, and label the images as KiCad renders.

Regenerate all README previews (front/back PNGs and schematic SVG/PDF) from the saved design, running from the repository root with Python 3, KiCad 10, and its standard 3D model libraries installed:

```sh
python3 docs/render-readme.py
```

Use `--only schematic` to refresh just the SVG and PDF, or `--only pcb` for the two 3D renders.
