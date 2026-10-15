# PCB Business Card with NFC

A thin, wallet-size PCB business card combining printed contact details, a vCard
QR code, custom copper and silkscreen artwork, and passive NFC.

<p>
  <img src="docs/business-card-front.png" width="30%" alt="KiCad render of the card's front, showing the lantern artwork, LED, circuitry, and NFC antenna">
  <img src="docs/business-card-back.png" width="68%" alt="KiCad render of the card's back, showing contact details, CH logo, and vCard QR code">
</p>

*KiCad 3D renders of the front and back, with gold on exposed copper.*

## Schematic

The design uses an NXP NT3H2111W0FHKH (NTAG I2C Plus) and a printed antenna for
tap-to-share contact information. It is designed to harvest energy from the NFC
reader's field to illuminate an LED, with no onboard battery or microcontroller.

[![KiCad export of the main schematic page](docs/business-card-schematic.svg)](docs/business-card-schematic.pdf)

## Project files

Open [business-card.kicad_pro](business-card.kicad_pro) in **KiCad 10** to explore
the design:

- [business-card.kicad_sch](business-card.kicad_sch) — circuit schematic.
- [business-card.kicad_pcb](business-card.kicad_pcb) — PCB layout.
- [business-card.kicad_sym](business-card.kicad_sym) — project symbols.
- [business-card.pretty/](business-card.pretty/) — project footprints.
- [business-card.3dshapes/](business-card.3dshapes/) — project 3D models.
- [artwork/](artwork/) — SVG artwork and previews used to generate footprints.

## Personalize and export

In the schematic, open **INFO1** properties and edit its `CONTACT_*` fields.
Use **Update PCB from Schematic (F8)** with **Update footprint fields from
symbols** enabled to copy the details to the PCB. The
[contact-info footprint](business-card.pretty/Contact_Info_SilkScreen.kicad_mod)
uses those fields for its printed text and native vCard QR code.
Company, role, phone, email and website are optional.
After F8, **save and reopen the PCB** to refresh KiCad 10's cached QR pattern.
If a footprint library update restores default contact values, repeat F8 and
the QR refresh to reapply INFO1.

For export-only overrides, copy [.env.example](.env.example) to `.env`.
Omitted keys keep the schematic INFO1 value; blank values clear optional fields
and omit them from the exported QR, vCard and NFC data.

With [uv](https://docs.astral.sh/uv/), KiCad 10 and its standard 3D model libraries
installed, run from this directory:

```sh
uv run finalize-card.py
uv run finalize-card.py --env .env.personal --output output/personal
```

`uv` installs the dotenv dependency automatically. The script copies the contact
fields into the output schematic and PCB, refreshes the native QR, and exports it.
The source project stays unchanged during export.
Generated QR and NFC data are fixed snapshots; change the source INFO1 fields
and rerun the exporter for a new bundle.

The output directory and matching ZIP include the personalized KiCad sources,
fabrication files (`fab.zip`), assembly files, front/back KiCad renders,
schematic SVG/PDF, vCard/NDEF contact files, and DRC/ERC reports. The default
destination is a new timestamped directory under `output/`. Existing output
destinations are never overwritten. Review `BUILD.txt` and the reports before
ordering: design errors are reported but do not prevent artifact export.
Program the exported NFC contact data onto the assembled card separately.

## Fabrication

Fabrication targets a two-layer, 0.6 mm FR-4 board with 1 oz copper, black solder
mask, and lead-free HASL.

Antenna tuning, NFC read range, and LED brightness require validation on
assembled hardware.
