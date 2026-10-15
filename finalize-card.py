#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = ["python-dotenv>=1.0,<2"]
# ///
"""Personalize the KiCad project and export Gerbers/drills, using optional .env overrides."""

import argparse
from datetime import datetime
import json
from pathlib import Path
import re
import shutil
from string import Template
import subprocess
import sys
import tempfile

from dotenv import dotenv_values
from dotenv.parser import parse_stream

ROOT = Path(__file__).resolve().parent
BASE = "business-card"
CONTACT_FIELDS = (
    "CONTACT_NAME", "CONTACT_ROLE", "CONTACT_COMPANY", "CONTACT_EMAIL",
    "CONTACT_PHONE", "CONTACT_WEB", "CONTACT_WEB_QR",
)
TOKENS = re.compile(r'"(?:\\.|[^"\\])*"|[()]|[^\s()"]+')


def contact_fields(document: str, item_kind: str) -> dict[str, re.Match[str]]:
    """Find value tokens on the placed INFO1, excluding embedded library symbols."""
    stack: list[str | None] = []
    properties: list[tuple[str, re.Match[str]]] = []
    property_values: list[re.Match[str]] = []
    matches: list[list[tuple[str, re.Match[str]]]] = []
    for token in TOKENS.finditer(document):
        value = token.group()
        if value == "(":
            stack.append(None)
        elif value == ")":
            item = stack.pop()
            if item == "property" and len(stack) == 2 and stack[-1] == item_kind:
                name, field_value = property_values[:2]
                field_name = json.loads(name.group()) if name.group().startswith('"') else name.group()
                properties.append((field_name, field_value))
            elif item == item_kind and len(stack) == 1:
                if any(name == "Reference" and json.loads(value.group()) == "INFO1"
                       for name, value in properties):
                    matches.append(properties)
        elif stack[-1] is None:
            stack[-1] = value
            if len(stack) == 2 and value == item_kind:
                properties = []
            elif len(stack) == 3 and value == "property":
                property_values = []
        elif len(stack) == 3 and stack[-2:] == [item_kind, "property"]:
            property_values.append(token)
    if len(matches) != 1:
        raise ValueError(f"Expected exactly one placed INFO1 {item_kind}.")
    fields: dict[str, re.Match[str]] = {}
    for name, field_value in matches[0]:
        if name in CONTACT_FIELDS:
            if name in fields:
                raise ValueError(f"Duplicate INFO1 {name} field in {item_kind}.")
            fields[name] = field_value
    missing = set(CONTACT_FIELDS) - fields.keys()
    if missing:
        raise ValueError(f"Missing INFO1 contact fields in {item_kind}: {', '.join(sorted(missing))}")
    return fields


def replace_values(document: str, replacements: list[tuple[re.Match[str], str]]) -> str:
    """Replace quoted values while preserving all surrounding KiCad source text."""
    for token, value in sorted(replacements, key=lambda pair: pair[0].start(), reverse=True):
        document = (document[:token.start()] + json.dumps(value, ensure_ascii=False)
                    + document[token.end():])
    return document


def vcard_qr(board: str) -> re.Match[str]:
    """Locate the vCard barcode's quoted text without rewriting other PCB data."""
    stack: list[str | None] = []
    matches: list[re.Match[str]] = []
    for token in TOKENS.finditer(board):
        value = token.group()
        if value == "(":
            stack.append(None)
        elif value == ")":
            stack.pop()
        elif stack[-1] is None:
            stack[-1] = value
        elif stack[-2:] == ["barcode", "text"] and value.startswith('"'):
            if json.loads(value).startswith("BEGIN:VCARD"):
                matches.append(token)
    if len(matches) != 1:
        raise ValueError("Expected exactly one vCard QR template in the PCB.")
    return matches[0]


def vcard_text(contact: dict[str, str], template: str) -> str:
    """Resolve the PCB's vCard template, escaping text and folding UTF-8 lines."""
    escaped = {key: value.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,")
               for key, value in contact.items()}
    lines = []
    for template_line in template.splitlines():
        line = Template(template_line).substitute(contact if template_line.startswith("URL:") else escaped)
        if not line.partition(":")[2]:
            continue  # Omit empty optional properties.
        part = ""
        for char in line:
            if len((part + char).encode("utf-8")) > 75:
                lines.append(part)
                part = " "
            part += char
        lines.append(part)
    return "\r\n".join(lines) + "\r\n"


def export(root: Path) -> None:
    """Export the two-layer board's fabrication files with KiCad."""
    pcb = f"{BASE}.kicad_pcb"
    subprocess.run(
        ["kicad-cli", "pcb", "export", "gerbers", "--check-zones",
         "--layers", "F.Cu,B.Cu,F.Mask,B.Mask,F.SilkS,B.SilkS,Edge.Cuts",
         "--no-protel-ext", "-o", "fab/", pcb],
        cwd=root, check=True,
    )
    subprocess.run(
        ["kicad-cli", "pcb", "export", "drill", "--format", "excellon",
         "--excellon-units", "mm", "--drill-origin", "absolute",
         "--excellon-separate-th", "-o", "fab/", pcb],
        cwd=root, check=True,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env", type=Path, help="optional overrides (default: .env in the repository root)")
    parser.add_argument("--output", type=Path, help="new output directory (default: output/<timestamp>)")
    args = parser.parse_args()
    schematic = (ROOT / f"{BASE}.kicad_sch").read_text()
    schematic_fields = contact_fields(schematic, "symbol")
    contact: dict[str, str] = {
        name: json.loads(value.group()) for name, value in schematic_fields.items()
    }
    env = args.env if args.env is not None else ROOT / ".env"
    if args.env is not None and not env.is_file():
        raise ValueError(f"Contact file does not exist: {env}")
    if env.is_file():
        with env.open(encoding="utf-8") as stream:
            for binding in parse_stream(stream):
                if binding.error:
                    raise ValueError(f"Invalid .env entry at {env}:{binding.original.line}")
    overrides = dotenv_values(env, interpolate=False) if env.is_file() else {}
    for key, value in overrides.items():
        if key not in CONTACT_FIELDS or value is None:
            raise ValueError(f"Use an INFO1 CONTACT_* field with a value: {key}")
        contact[key] = value
    if not contact["CONTACT_NAME"].strip():
        raise ValueError("CONTACT_NAME is required.")
    for key, value in contact.items():
        if any(ord(c) < 32 for c in value) or "${" in value or "@{" in value:
            raise ValueError(f"{key} must be a single line of literal text.")
    board = (ROOT / f"{BASE}.kicad_pcb").read_text()
    board_fields = contact_fields(board, "footprint")
    qr = vcard_qr(board)
    vcard = vcard_text(contact, json.loads(qr.group()))
    schematic = replace_values(schematic, [(token, contact[name]) for name, token in schematic_fields.items()])
    board = replace_values(board, [(token, contact[name]) for name, token in board_fields.items()]
                           + [(qr, vcard)])
    output = (args.output or ROOT / "output" / datetime.now().strftime("%Y%m%d-%H%M%S")).resolve()
    zipped = output.with_name(output.name + ".zip")
    if output.exists() or zipped.exists():
        raise ValueError(f"Output already exists; choose a new --output directory: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".card-build-", dir=output.parent) as temporary:
        stage = Path(temporary) / "bundle"
        (stage / "fab").mkdir(parents=True)
        for extension in ("kicad_pcb", "kicad_sch", "kicad_pro", "kicad_dru", "kicad_sym"):
            shutil.copy2(ROOT / f"{BASE}.{extension}", stage)
        for name in ("fp-lib-table", "sym-lib-table", "LICENSE"):
            shutil.copy2(ROOT / name, stage)
        for name in (f"{BASE}.pretty", f"{BASE}.3dshapes"):
            shutil.copytree(ROOT / name, stage / name)
        (stage / f"{BASE}.kicad_sch").write_text(schematic)
        (stage / f"{BASE}.kicad_pcb").write_text(board)
        export(stage)
        archive = Path(shutil.make_archive(str(Path(temporary) / "bundle"), "zip", stage))
        if output.exists() or zipped.exists():
            raise ValueError("Output appeared during the build; choose a new destination.")
        stage.rename(output)
        archive.rename(zipped)
    print(f"\nKiCad project and fabrication files: {output}\nZIP: {zipped}")


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, KeyError, subprocess.CalledProcessError) as error:
        sys.exit(f"Error: {error}")
