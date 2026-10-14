"""Generate an independently drawn Lite-On LTST-C230KFKT reverse-mount LED.

Run with a Python interpreter that can import FreeCAD, Part, and Import:
  PYTHONPATH=/usr/lib/freecad-python3/lib /usr/bin/python3 generate_ltst_c230kfkt.py

Source: Lite-On LTST-C230KFKT datasheet, BNS-OD-C131/A4, package drawing p1
and suggested soldering pattern p7:
https://media.digikey.com/pdf/Data%20Sheets/Lite-On%20PDFs/LTST-C230KFKT_5-24-06.pdf

Starter reference: LIB_LTST-C230KFKT.zip, SamacSys part 470259:
https://componentsearchengine.com/part-view/LTST-C230KFKT/Lite-On
Symbol, footprint, and STEP were independently drawn from manufacturer
dimensions; no SamacSys library geometry was copied.

All dimensions are millimeters. The package outline is 3.20 x 1.60,
the carrier thickness is 0.28, and the complete package thickness is 1.10.
The central lens is 1.50 long. Its 0.82 projection is derived as 1.10-0.28.
Rear contact areas are 0.50 long x 1.00 wide. Front contact length 0.85
is derived from (3.20-1.50)/2. The castellation width is 0.50; its
semicircular profile is an interpretation of the drawing. The general
tolerance is +/-0.10; this model represents nominal dimensions only.

The source does not fully dimension optical and cosmetic details. The
rectangular untapered lens, 0.015 metal thickness, 0.20-cube die,
0.01-thick cathode-mask inlay, mask
outline, colors, and lens display opacity are visual simplifications.
The die center is 0.25 toward the cathode, derived from the 1.35 reference
dimension to the cathode end. Bond wires and microscopic features are
omitted. Display transparency is not an optical simulation.

Origin is the center of the footprint at the solder contact plane, Z=0.
Pin 1/cathode is at negative X, pin 2/anode is at positive X. The carrier
extends upward to Z=+0.28; the lens projects DOWN into the PCB opening to
Z=-0.82. Attach to a front-side KiCad footprint with zero model rotation
and zero offset. KiCad mirrors the complete footprint for back mounting.
"""

from pathlib import Path

import FreeCAD as App
import Part
import Import  # Part must initialize before the STEP importer/exporter.


MODEL_NAME = "LiteOn_LTST-C230KFKT_ReverseMount"
LENGTH = 3.20
WIDTH = 1.60
CARRIER_THICKNESS = 0.28
TOTAL_THICKNESS = 1.10
LENS_LENGTH = 1.50
LENS_PROJECTION = TOTAL_THICKNESS - CARRIER_THICKNESS
METAL_THICKNESS = 0.015
CASTELLATION_RADIUS = 0.25


def box(x, y, z, sx, sy, sz):
    return Part.makeBox(sx, sy, sz, App.Vector(x, y, z))


def build(output):
    doc = App.newDocument("LiteOn_LTST_C230KFKT")
    objects = []

    def feature(name, shape, color):
        shape = shape.removeSplitter()
        assert shape.isValid() and len(shape.Solids) == 1, name
        obj = doc.addObject("Part::Feature", name)
        obj.Label = name
        obj.Shape = shape
        # RGB/RGBA face colors export in headless FreeCAD. RGBA's final
        # component is opacity; STEP stores the complementary transparency.
        objects.append((obj, [color] * len(shape.Faces)))
        return obj

    carrier_envelope = box(-LENGTH / 2, -WIDTH / 2, 0,
                           LENGTH, WIDTH, CARRIER_THICKNESS)
    carrier = carrier_envelope
    contacts = []
    for side in (-1, 1):
        end_x = side * LENGTH / 2
        notch = Part.makeCylinder(CASTELLATION_RADIUS, CARRIER_THICKNESS,
                                  App.Vector(end_x, 0, 0))
        outer_notch = Part.makeCylinder(
            CASTELLATION_RADIUS + METAL_THICKNESS, CARRIER_THICKNESS,
            App.Vector(end_x, 0, 0))
        plating = outer_notch.cut(notch).common(carrier_envelope)
        front_x = -LENGTH / 2 if side == -1 else LENS_LENGTH / 2
        front = box(front_x, -WIDTH / 2, 0,
                    (LENGTH - LENS_LENGTH) / 2, WIDTH, METAL_THICKNESS)
        rear_x = -LENGTH / 2 if side == -1 else LENGTH / 2 - 0.50
        rear = box(rear_x, -0.50, CARRIER_THICKNESS - METAL_THICKNESS,
                   0.50, 1.00, METAL_THICKNESS)
        terminal = front.fuse(rear).fuse(plating).cut(notch).removeSplitter()
        contacts.append(terminal)
        carrier = carrier.cut(notch).cut(terminal)

    # T stem points toward the cathode. The marker is flush with the rear
    # surface, keeping the specified overall thickness intact.
    mask_z = CARRIER_THICKNESS - 0.01
    cathode_mask = box(-0.15, -WIDTH / 2, mask_z, 0.30, WIDTH, 0.01).fuse(
        box(-0.75, -0.30, mask_z, 0.60, 0.60, 0.01)).removeSplitter()
    carrier = carrier.cut(cathode_mask)

    die = box(-0.35, -0.10, -0.20, 0.20, 0.20, 0.20)
    lens = box(-LENS_LENGTH / 2, -WIDTH / 2, -LENS_PROJECTION,
               LENS_LENGTH, WIDTH, LENS_PROJECTION).cut(die)

    feature("PCB_carrier", carrier, (0.88, 0.87, 0.77))
    feature("Terminal_1_cathode", contacts[0], (0.78, 0.62, 0.27))
    feature("Terminal_2_anode", contacts[1], (0.78, 0.62, 0.27))
    feature("Cathode_mask", cathode_mask, (0.10, 0.14, 0.10))
    feature("Orange_LED_die", die, (0.88, 0.33, 0.06))
    feature("Water_clear_lens", lens, (0.94, 0.97, 1.00, 0.22))
    doc.recompute()

    bounds = App.BoundBox()
    volume = 0.0
    for index, (obj, _) in enumerate(objects):
        bounds.add(obj.Shape.BoundBox)
        volume += obj.Shape.Volume
        for other, _ in objects[index + 1:]:
            assert obj.Shape.common(other.Shape).Volume < 1e-9, (
                obj.Label, other.Label, "overlapping solids")
    expected_bounds = (-LENGTH / 2, LENGTH / 2, -WIDTH / 2, WIDTH / 2,
                       -LENS_PROJECTION, CARRIER_THICKNESS)
    for actual, expected in zip((bounds.XMin, bounds.XMax, bounds.YMin,
                                  bounds.YMax, bounds.ZMin, bounds.ZMax),
                                 expected_bounds):
        assert abs(actual - expected) < 1e-7, (actual, expected)
    for terminal in contacts:
        assert abs(terminal.BoundBox.ZMin) < 1e-7
    assert contacts[0].BoundBox.XMax < 0 < contacts[1].BoundBox.XMin

    Import.export(objects, str(output))
    loaded = Part.read(str(output))
    assert loaded.isValid() and len(loaded.Solids) == len(objects) == 6
    assert abs(loaded.Volume - volume) < 1e-7
    loaded_bounds = loaded.BoundBox
    for actual, expected in zip((loaded_bounds.XMin, loaded_bounds.XMax,
                                  loaded_bounds.YMin, loaded_bounds.YMax,
                                  loaded_bounds.ZMin, loaded_bounds.ZMax),
                                 expected_bounds):
        assert abs(actual - expected) < 1e-7, (actual, expected)
    assert "SURFACE_STYLE_TRANSPARENT" in output.read_text()
    App.closeDocument(doc.Name)
    print(f"Saved {output}: 3.20 x 1.60 x 1.10 mm, 6 valid nonoverlapping solids")
    print("Seating plane Z=0; carrier Z=0..+0.28; lens Z=-0.82..0; cathode X<0")


if __name__ == "__main__":
    build(Path(__file__).resolve().with_name(MODEL_NAME + ".step"))
