#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = ["python-dotenv>=1.0,<2"]
# ///
"""Copy the KiCad project, personalize INFO1, then export fabrication files and previews."""

import argparse
import json
import re
import shutil
import subprocess
import sys
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parent
BASE = "business-card"
CONTACT_FIELDS = {
    "CONTACT_NAME", "CONTACT_ROLE", "CONTACT_COMPANY", "CONTACT_EMAIL",
    "CONTACT_PHONE", "CONTACT_WEB", "CONTACT_WEB_QR",
}
# Match the saved KiCad format, including escaped quotes inside field values.
FIELD = re.compile(
    r'(?m)^(?P<prefix>\t\t\(property "(?P<name>CONTACT_[A-Z_]+)" )'
    r'(?P<value>"(?:\\.|[^"\\])*")'
)


def info1(document: str) -> str:
    """Select the placed INFO1 block; library symbols have deeper indentation."""
    blocks = re.findall(r'(?ms)^\t\((?:symbol|footprint)\b.*?^\t\)', document)
    matches = [block for block in blocks if '\n\t\t(property "Reference" "INFO1"' in block]
    if len(matches) != 1:
        raise ValueError("Expected exactly one placed INFO1 symbol or footprint.")
    fields = list(FIELD.finditer(matches[0]))
    if len(fields) != len(CONTACT_FIELDS) or {field["name"] for field in fields} != CONTACT_FIELDS:
        raise ValueError("INFO1 must contain each of the seven CONTACT_* fields once.")
    return matches[0]


def replace_contact(document: str, contact: dict[str, str]) -> str:
    """Replace only INFO1's contact values, leaving the surrounding file intact."""
    original = info1(document)
    updated = FIELD.sub(
        lambda field: field["prefix"] + json.dumps(contact[field["name"]], ensure_ascii=False),
        original,
    )
    return document.replace(original, updated, 1)


def export(output: Path) -> None:
    """Run the KiCad checks, fabrication exports, and existing preview renderer."""
    pcb = f"{BASE}.kicad_pcb"
    cli: Callable[..., subprocess.CompletedProcess[bytes]] = lambda *args: subprocess.run(
        ["kicad-cli", *args], cwd=output, check=True,
    )

    cli("pcb", "drc", "--schematic-parity", "--refill-zones", "--save-board",
        "-o", "drc.rpt", pcb)
    cli("pcb", "export", "gerbers", "--no-protel-ext",
        "--layers", "F.Cu,B.Cu,F.Mask,B.Mask,F.SilkS,B.SilkS,Edge.Cuts", "-o", "fab/", pcb)
    cli("pcb", "export", "drill", "--format", "excellon", "--excellon-units", "mm",
        "--drill-origin", "absolute", "--excellon-separate-th", "--generate-map",
        "--map-format", "pdf", "-o", "fab/", pcb)
    subprocess.run(
        [sys.executable, str(ROOT / "docs/render-readme.py")],
        cwd=output, check=True,
    )
    (output / f"{BASE}.kicad_prl").unlink(missing_ok=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env", type=Path, default=ROOT / ".env",
                        help="optional overrides (default: .env)")
    parser.add_argument("--output", type=Path,
                        default=ROOT / "output" / datetime.now().strftime("%Y%m%d-%H%M%S"),
                        help="new directory (default: output/<timestamp>)")
    args = parser.parse_args()
    if args.env != parser.get_default("env") and not args.env.is_file():
        parser.error(f"Contact file does not exist: {args.env}")

    # 1. Read INFO1 and any contact details supplied in .env.
    schematic = (ROOT / f"{BASE}.kicad_sch").read_text(encoding="utf-8")
    contact: dict[str, str] = {
        field["name"]: json.loads(field["value"]) for field in FIELD.finditer(info1(schematic))
    }
    overrides = dotenv_values(args.env, interpolate=False)
    contact.update({key: value for key, value in overrides.items()
                    if key in contact and value is not None})
    if not contact["CONTACT_NAME"].strip():
        raise ValueError("CONTACT_NAME is required.")
    for key, value in contact.items():
        if any(ord(char) < 32 for char in value) or "${" in value or "@{" in value:
            raise ValueError(f"{key} must be a single line of literal text.")

    # 2. Copy the project, leaving out private settings, caches, and prior exports.
    output: Path = args.output.resolve()
    zipped = output.with_name(output.name + ".zip")
    if output.exists() or zipped.exists():
        raise ValueError(f"Output already exists; choose a new --output directory: {output}")
    ignore = shutil.ignore_patterns(
        ".*", "output", "card-output", output.name, args.env.name, "*.env",
        "__pycache__", "*.pyc", "*-backups", "_autosave-*", "~*.lck",
        "*.kicad_prl", "fp-info-cache",
    )
    shutil.copytree(
        ROOT, output,
        ignore=lambda directory, names: ignore(directory, names) - {".env.example", ".gitignore"},
    )
    (output / "fab").mkdir(exist_ok=True)
    (output / "docs").mkdir(exist_ok=True)

    # 3. Set INFO1's fields and copy them to the PCB, like Update PCB from Schematic.
    schematic = replace_contact(schematic, contact)
    board = replace_contact((ROOT / f"{BASE}.kicad_pcb").read_text(encoding="utf-8"), contact)
    (output / f"{BASE}.kicad_sch").write_text(schematic, encoding="utf-8")
    (output / f"{BASE}.kicad_pcb").write_text(board, encoding="utf-8")

    # 4. Reopen in KiCad, refill/check the board, and export fabrication files and previews.
    export(output)

    # 5. Zip the finished project copy.
    with ZipFile(zipped, "x", ZIP_DEFLATED) as archive:
        for path in output.rglob("*"):
            if path.is_file():
                archive.write(path, path.relative_to(output))
    print(f"\nFinalized project: {output}\nZIP: {zipped}")


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        sys.exit(f"Error: {error}")
