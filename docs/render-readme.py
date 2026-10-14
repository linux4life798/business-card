#!/usr/bin/env python3
"""Render README previews from the saved KiCad PCB and main schematic page."""

import argparse
from pathlib import Path
import re
import shutil
import subprocess
import tempfile


def render_pcb(root, temporary):
    source = root / "business-card.kicad_pcb"
    board, count = re.subn(
        r'\(copper_finish "[^"]*"\)',
        '(copper_finish "ENIG")',
        source.read_text(),
    )
    if count != 1:
        raise SystemExit("Expected one copper_finish setting in the saved PCB.")

    # Keep project-local models resolvable from the temporary board directory.
    board = board.replace("${KIPRJMOD}", root.as_posix())
    views = (
        ("front", ["--width", "1000", "--height", "1500", "--side", "top",
                   "--rotate", "0,0,-90", "--zoom", "0.9"]),
        ("back", ["--width", "1500", "--height", "1000", "--side", "bottom",
                  "--zoom", "1.2"]),
    )

    render_board = temporary / source.name
    render_board.write_text(board)
    shutil.copy2(root / "business-card.kicad_pro", temporary)
    for side, options in views:
        subprocess.run(
            ["kicad-cli", "pcb", "render", "--output",
             str(temporary / f"business-card-{side}.png"),
             *options, "--background", "transparent", "--quality", "high",
             "--use-board-stackup-colors", str(render_board)],
            cwd=root,
            check=True,
        )
    return [f"business-card-{side}.png" for side, _ in views]


def render_schematic(root, temporary):
    source = root / "business-card.kicad_sch"
    # Pin the built-in light theme, including its opaque background, so the
    # preview is independent of local preferences and readable in dark READMEs.
    options = ["--pages", "1", "--theme", "_builtin_default"]
    subprocess.run(
        ["kicad-cli", "sch", "export", "svg", *options,
         "--output", str(temporary), str(source)],
        cwd=root,
        check=True,
    )
    svg = "business-card-schematic.svg"
    (temporary / f"{source.stem}.svg").rename(temporary / svg)
    pdf = "business-card-schematic.pdf"
    subprocess.run(
        ["kicad-cli", "sch", "export", "pdf", *options,
         "--exclude-pdf-property-popups", "--output", str(temporary / pdf),
         str(source)],
        cwd=root,
        check=True,
    )
    return [svg, pdf]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--only", choices=("all", "pcb", "schematic"), default="all",
        help="select previews to regenerate (default: all)",
    )
    args = parser.parse_args()
    root = Path(__file__).resolve().parent.parent
    with tempfile.TemporaryDirectory(prefix="business-card-readme-") as directory:
        temporary = Path(directory)
        filenames = []
        if args.only in ("all", "pcb"):
            filenames.extend(render_pcb(root, temporary))
        if args.only in ("all", "schematic"):
            filenames.extend(render_schematic(root, temporary))
        # Publish only after all requested exports succeed.
        for filename in filenames:
            shutil.copy2(temporary / filename, root / "docs" / filename)


if __name__ == "__main__":
    main()
