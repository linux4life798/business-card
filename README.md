# PCB Business Card with NFC

A thin, wallet-size PCB business card combining printed contact details, a vCard
QR code, custom copper and silkscreen artwork, and passive NFC.

<p>
  <img src="docs/business-card-front.png" width="30%" alt="KiCad render of the card's front, showing the lantern artwork, LED, circuitry, and NFC antenna">
  <img src="docs/business-card-back.png" width="68%" alt="KiCad render of the card's back, showing contact details, CH logo, and vCard QR code">
</p>

*KiCad 3D renders of the front and back, with gold on exposed copper.*

## Make it yours

You can personalize and export the card entirely through **KiCad 10**.
Python and GitHub Actions are optional conveniences.

1. Download or clone the whole project folder and open
   [business-card.kicad_pro](business-card.kicad_pro).
2. In the schematic, open **INFO1** properties and edit its `CONTACT_*` fields.
   Company, role, phone, email and website are optional. `CONTACT_WEB` is the
   printed address; `CONTACT_WEB_QR` is the QR's full URL, including `https://`.
3. Use **Update PCB from Schematic (F8)** with **Update footprint fields from
   symbols** enabled.
4. **Save, close and reopen the PCB Editor** to refresh KiCad 10's QR pattern.
   Check the text layout and scan the QR to confirm your details.
5. Run **Inspect → Design Rules Checker** and review its findings. Export Gerbers
   and drill files from **File → Fabrication Outputs** when ready to order.

<details>
<summary>Optional: automated exports</summary>

The [finalizer](copy-and-customize.py) creates a personalized project copy and export
bundle. It uses the saved INFO1 values; to override them only in the exported
copy, copy [contact.example.toml](contact.example.toml) to `contact.toml` and edit
it. Omitted keys keep the INFO1 value; `""` clears an optional field. For CI,
`CONTACT_*` environment variables override both TOML and INFO1, including empty values.

Use Python 3.11+ with KiCad 10's `kicad-cli` on your PATH and standard 3D model
libraries installed. No pip packages or virtual environment are needed:

```sh
python3 copy-and-customize.py
python3 copy-and-customize.py --config contact.personal.toml --output output/personal
```

On Windows, use `python` instead of `python3`. The **KiCad 10 Command Prompt**
provides access to `kicad-cli`.

The bundle contains a project-folder copy, Gerbers/drills and drill-map PDFs in
`fab/`, refreshed schematic SVG/PDF and front/back renders in `docs/`, and `drc.rpt`.
Local settings, contact files, caches and previous exports are excluded.
It defaults to `output/<timestamp>/` plus one ZIP, preserving source files and
existing exports. Review the report and previews before ordering; DRC findings
do not prevent export. The exported project remains editable through the same
INFO1 workflow; regenerate fabrication files after further edits.

For builds on GitHub, see the [private-repository action and starter workflow](automation/README.md).

</details>

## Explore the design

The NFC circuit uses an NXP NT3H2111W0FHKH (NTAG I2C Plus) and a printed antenna.
It is designed to illuminate an LED using energy from the reader's field,
with no onboard battery or microcontroller.

[![KiCad export of the main schematic page](docs/business-card-schematic.svg)](docs/business-card-schematic.pdf)

- [Schematic](business-card.kicad_sch) and [PCB layout](business-card.kicad_pcb).
- Project [symbols](business-card.kicad_sym), [footprints](business-card.pretty/)
  and [3D models](business-card.3dshapes/).
- [Artwork](artwork/) and its source SVGs.

INFO1 supplies the fields used by the
[contact-info footprint](business-card.pretty/Contact_Info_SilkScreen.kicad_mod)
for its text and native QR. If a footprint library update restores default
contact values, repeat F8 and the save/reopen step to reapply your details.

## Fabrication

Fabrication targets a two-layer, 0.6 mm FR-4 board with 1 oz copper, black solder
mask, and lead-free HASL.

Antenna tuning, NFC read range, and LED brightness require validation on
assembled hardware.
