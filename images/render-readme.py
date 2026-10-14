#!/usr/bin/env python3
"""Render README images in KiCad with gold on exposed copper."""

from pathlib import Path
import re
import shutil
import subprocess
import tempfile


def main():
    root = Path(__file__).resolve().parent.parent
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

    with tempfile.TemporaryDirectory(prefix="business-card-readme-") as directory:
        temporary = Path(directory)
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
        for side, _ in views:
            filename = f"business-card-{side}.png"
            shutil.copy2(temporary / filename, Path(__file__).resolve().parent / filename)


if __name__ == "__main__":
    main()
