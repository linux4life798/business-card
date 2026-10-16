#!/usr/bin/env python3
"""Exercise contact overrides and project copies without fabrication exports."""

import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import re
import shutil
import tempfile
import tomllib
import unittest
from unittest import mock
import zipfile

ROOT = Path(__file__).resolve().parent.parent
SPEC = importlib.util.spec_from_file_location("finalize_card", ROOT / "finalize-card.py")
FINALIZER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(FINALIZER)


class ActionContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="card-contract-test-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.source = self.root / "project"
        self.source.mkdir()
        self.output = self.root / "bundle"
        for suffix in ("kicad_sch", "kicad_pcb", "kicad_pro"):
            shutil.copy2(ROOT / f"business-card.{suffix}", self.source)
        self.schematic = (self.source / "business-card.kicad_sch").read_text()
        self.board = (self.source / "business-card.kicad_pcb").read_bytes()
        self.project = (self.source / "business-card.kicad_pro").read_bytes()
        self.defaults = self.contact_fields(self.schematic)
        self.environment = {key: value for key, value in os.environ.items()
                            if key not in FINALIZER.CONTACT_FIELDS}
        self.addCleanup(mock.patch.stopall)
        mock.patch.object(FINALIZER, "ROOT", self.source).start()
        mock.patch.dict(os.environ, self.environment, clear=True).start()

    @staticmethod
    def contact_fields(document: str) -> dict[str, str]:
        return {field["name"]: json.loads(field["value"])
                for field in FINALIZER.FIELD.finditer(FINALIZER.info1(document))}

    @staticmethod
    def without_contact_values(document: bytes) -> bytes:
        return re.sub(rb'(?m)^(\t\t\(property "CONTACT_[A-Z_]+" )"(?:\\.|[^"\\])*"',
                      rb'\1"<contact>"', document)

    def run_finalizer(self, config: str | None = "", environment: dict[str, str] | None = None,
                      config_path: Path | None = None) -> dict[str, str]:
        arguments = ["finalize-card.py", "--output", str(self.output)]
        if config is not None:
            config_path = config_path or self.source / "contact.personal.toml"
            config_path.write_text(config, encoding="utf-8")
            arguments.extend(["--config", str(config_path)])
        elif config_path is not None:
            arguments.extend(["--config", str(config_path)])
        with mock.patch.object(FINALIZER.sys, "argv", arguments), \
                mock.patch.object(FINALIZER, "export") as export, \
                mock.patch.dict(os.environ, environment or {}), \
                contextlib.redirect_stdout(io.StringIO()):
            FINALIZER.main()
        export.assert_called_once_with(self.output)
        schematic = (self.output / "business-card.kicad_sch").read_text()
        contact = self.contact_fields(schematic)
        for suffix in ("kicad_sch", "kicad_pcb"):
            original = (self.source / f"business-card.{suffix}").read_bytes()
            updated = (self.output / f"business-card.{suffix}").read_bytes()
            self.assertEqual(self.contact_fields(updated.decode()), contact)
            self.assertEqual(self.without_contact_values(updated), self.without_contact_values(original))
            self.assertEqual(re.findall(rb'\$\{[^}]+\}', updated),
                             re.findall(rb'\$\{[^}]+\}', original))
        self.assertIn(b'FN:${CONTACT_NAME}', (self.output / "business-card.kicad_pcb").read_bytes())
        self.assertEqual((self.output / "business-card.kicad_pro").read_bytes(), self.project)
        self.assertTrue((self.output / "docs").is_dir())
        self.assertTrue((self.output / "fab").is_dir())
        self.assertEqual((self.source / "business-card.kicad_pcb").read_bytes(), self.board)
        return contact

    def test_example_personalizes_project_and_keeps_editable_qr(self) -> None:
        example = ROOT / "contact.example.toml"
        expected = tomllib.loads(example.read_text())
        contact = self.run_finalizer(example.read_text())
        self.assertEqual(contact, expected)
        self.assertEqual((self.source / "business-card.kicad_sch").read_text(), self.schematic)
        with zipfile.ZipFile(self.output.with_suffix(".zip")) as archive:
            self.assertIsNone(archive.testzip())
            self.assertEqual(archive.read("business-card.kicad_pcb"),
                             (self.output / "business-card.kicad_pcb").read_bytes())
            self.assertNotIn("contact.personal.toml", archive.namelist())
            self.assertFalse(any(name.endswith((".ndef", ".vcf")) for name in archive.namelist()))

    def test_environment_overrides_toml_and_omitted_fields_keep_info1(self) -> None:
        contact = self.run_finalizer(
            'CONTACT_NAME = "TOML Name"\nCONTACT_EMAIL = "toml@example.com"\n'
            'CONTACT_COMPANY = "TOML Company"\n',
            {"CONTACT_NAME": "CI Name", "CONTACT_COMPANY": ""},
        )
        self.assertEqual(contact["CONTACT_NAME"], "CI Name")
        self.assertEqual(contact["CONTACT_EMAIL"], "toml@example.com")
        self.assertEqual(contact["CONTACT_COMPANY"], "")
        self.assertEqual(contact["CONTACT_ROLE"], self.defaults["CONTACT_ROLE"])

    def test_environment_only_requires_no_contact_file(self) -> None:
        contact = self.run_finalizer(None, {"CONTACT_NAME": "CI Name"})
        self.assertEqual(contact["CONTACT_NAME"], "CI Name")
        self.assertEqual(contact["CONTACT_EMAIL"], self.defaults["CONTACT_EMAIL"])

    def test_default_contact_toml_is_optional_and_loaded_when_present(self) -> None:
        (self.source / "contact.toml").write_text('CONTACT_NAME = "Default TOML Name"\n')
        contact = self.run_finalizer(None)
        self.assertEqual(contact["CONTACT_NAME"], "Default TOML Name")
        self.assertFalse((self.output / "contact.toml").exists())

    def test_empty_optional_fields_and_unicode_round_trip(self) -> None:
        company = 'Example "R&D"; 工房, Inc. (West) \\ studio'
        contact = self.run_finalizer(
            f'CONTACT_NAME = "Élodie Example"\nCONTACT_COMPANY = {json.dumps(company)}\n'
            'CONTACT_ROLE = ""\nCONTACT_PHONE = ""\n',
        )
        self.assertEqual(contact["CONTACT_COMPANY"], company)
        self.assertEqual(contact["CONTACT_ROLE"], "")
        self.assertEqual(contact["CONTACT_PHONE"], "")

    def test_placed_schematic_is_the_source_for_omitted_overrides(self) -> None:
        original = FINALIZER.info1(self.schematic)
        updated = re.sub(r'\(property "CONTACT_NAME" "(?:\\.|[^"\\])*"',
                         '(property "CONTACT_NAME" "Saved schematic name"', original)
        schematic = self.schematic.replace(original, updated, 1)
        (self.source / "business-card.kicad_sch").write_text(schematic)
        contact = self.run_finalizer(None)
        self.assertEqual(contact["CONTACT_NAME"], "Saved schematic name")
        self.assertEqual((self.source / "business-card.kicad_sch").read_text(), schematic)

    def test_project_copy_preserves_assets_and_excludes_contact_files_and_recursion(self) -> None:
        kept = {
            "README.md": "Project instructions\n",
            "artwork/nested/logo.svg": "<svg/>\n",
            "contact.example.toml": 'CONTACT_NAME = "Example Name"\n',
            ".gitignore": "output/\n",
        }
        skipped = {
            ".git/config": "Local Git metadata\n",
            ".env.private": "CONTACT_NAME=Private Name\n",
            "contact.toml": 'CONTACT_NAME = "Private Name"\n',
            "contact.another.toml": 'CONTACT_NAME = "Private Name"\n',
            "legacy.env": "CONTACT_NAME=Private Name\n",
            "__pycache__/stale.pyc": "Cached bytecode\n",
            "output/previous.txt": "Previous export\n",
            "card-output/previous.zip": "Previous action export\n",
        }
        for name, content in (kept | skipped).items():
            path = self.source / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
        self.output = self.source / "exports" / "custom-card"
        self.run_finalizer('CONTACT_NAME = "Fixture Name"\n',
                           config_path=self.source / "custom[private].toml")
        for name, content in kept.items():
            self.assertEqual((self.output / name).read_text(), content)
        for name in (".git", ".env.private", "contact.toml", "contact.another.toml", "legacy.env",
                     "custom[private].toml", "__pycache__", "output", "card-output"):
            self.assertFalse((self.output / name).exists())
        self.assertFalse((self.output / "exports" / self.output.name).exists())

    def test_unknown_keys_do_not_change_saved_fields(self) -> None:
        self.assertEqual(self.run_finalizer('PROJ_CONTACT_NAME = "Ignored Name"\n'), self.defaults)

    def test_invalid_toml_is_rejected_before_output(self) -> None:
        with self.assertRaises(tomllib.TOMLDecodeError):
            self.run_finalizer('CONTACT_NAME = "Unclosed quote\n')
        self.assertFalse(self.output.exists())

    def test_non_string_contact_values_are_rejected_before_output(self) -> None:
        for value in ("123", "true", '["Company"]'):
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError, "CONTACT_COMPANY"):
                    self.run_finalizer(f"CONTACT_COMPANY = {value}\n")
                self.assertFalse(self.output.exists())

    def test_blank_name_from_environment_is_rejected_before_output(self) -> None:
        with self.assertRaisesRegex(ValueError, "CONTACT_NAME"):
            self.run_finalizer('CONTACT_NAME = "Valid TOML Name"\n', {"CONTACT_NAME": ""})
        self.assertFalse(self.output.exists())

    def test_missing_explicit_config_is_rejected(self) -> None:
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            self.run_finalizer(None, config_path=self.source / "missing.toml")
        self.assertFalse(self.output.exists())

    def test_existing_archive_is_preserved(self) -> None:
        archive = self.output.with_suffix(".zip")
        archive.write_bytes(b"Previous export")
        with self.assertRaisesRegex(ValueError, "already exists"):
            self.run_finalizer(None)
        self.assertEqual(archive.read_bytes(), b"Previous export")
        self.assertFalse(self.output.exists())

    def test_missing_or_ambiguous_info1_is_rejected(self) -> None:
        for kind, original in (("schematic", self.schematic), ("PCB", self.board.decode())):
            missing = original.replace('(property "Reference" "INFO1"', '(property "Reference" "OTHER"')
            for document in (missing, original + original):
                with self.subTest(kind=kind, document_length=len(document)):
                    with self.assertRaisesRegex(ValueError, "exactly one placed INFO1"):
                        FINALIZER.info1(document)

    def test_missing_or_duplicate_contact_fields_are_rejected(self) -> None:
        for kind, original in (("schematic", self.schematic), ("PCB", self.board.decode())):
            for replacement in ("UNRELATED", "CONTACT_NAME"):
                document = original.replace('(property "CONTACT_COMPANY"', f'(property "{replacement}"')
                with self.subTest(kind=kind, replacement=replacement):
                    with self.assertRaisesRegex(ValueError, "seven CONTACT_\\* fields once"):
                        FINALIZER.info1(document)


if __name__ == "__main__":
    unittest.main()
