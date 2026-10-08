"""Generate the project's independently drawn NXP SOT902-3 STEP model.

Run with a Python interpreter that can import FreeCAD, Part, and Import:
  PYTHONPATH=/usr/lib/freecad-python3/lib /usr/bin/python3 generate_nt3h2111.py

Source: NXP NT3H2111_2211 Rev. 3.6, Figure 31 (page 70):
https://www.nxp.com/docs/en/data-sheet/NT3H2111_2211.pdf

Dimensions are millimeters. D/E=1.60, b=0.20, L=0.40, b1/L1/L2=0.30
are nominal. A=0.50 is the specified MAXIMUM height, not a nominal value.
A1=0.025 is the midpoint of the specified 0..0.05 standoff range.
Terminal thickness (0.10), colors, and the flush orientation-dot inlay are
visual modeling choices: the drawing does not dimension these details.
This nominal-XY model does not include tolerance or mold/metal protrusions.

Origin is the body center at the contact seating plane, Z=0. Positive Y
is upward in the package top view; pin 1 is at upper left. The physical
0.30-square center metal is included but is NOT a solderable ninth pin.
"""

from pathlib import Path

import FreeCAD as App
import Part
import Import  # Part must initialize before the STEP importer/exporter.


MODEL_NAME = "NXP_SOT902-3_XQFN-8_1.6x1.6mm"
BODY_WIDTH = 1.60
MAX_HEIGHT = 0.50
STANDOFF = 0.025
METAL_THICKNESS = 0.10


def box(x, y, sx, sy):
    return Part.makeBox(sx, sy, METAL_THICKNESS, App.Vector(x, y, 0))


def build(output):
    doc = App.newDocument("NXP_SOT902_3")
    objects = []

    def feature(name, shape, color):
        assert shape.isValid() and len(shape.Solids) == 1, name
        obj = doc.addObject("Part::Feature", name)
        obj.Label = name
        obj.Shape = shape
        # Import.export accepts per-face colors without a GUI session.
        objects.append((obj, [color] * len(shape.Faces)))
        return obj

    pin1_points = [(-0.8, 0.4), (-0.4, 0.4), (-0.4, 0.6),
                   (-0.5, 0.6), (-0.5, 0.7), (-0.8, 0.7)]
    wire = Part.makePolygon([App.Vector(x, y, 0)
                             for x, y in pin1_points + [pin1_points[0]]])
    contacts = [
        Part.Face(wire).extrude(App.Vector(0, 0, METAL_THICKNESS)),
        box(-0.8, -0.1, 0.4, 0.2),  # 2: VSS
        box(-0.8, -0.6, 0.4, 0.2),  # 3: SCL
        box(-0.1, -0.8, 0.2, 0.4),  # 4: FD
        box(0.4, -0.6, 0.4, 0.2),   # 5: SDA
        box(0.4, -0.1, 0.4, 0.2),   # 6: VCC
        box(0.4, 0.4, 0.4, 0.2),    # 7: VOUT
        box(-0.1, 0.4, 0.2, 0.4),   # 8: LB
    ]
    center_metal = box(-0.15, -0.15, 0.30, 0.30)
    marker = Part.makeCylinder(0.085, 0.01, App.Vector(-0.50, 0.50, 0.49))
    body = Part.makeBox(BODY_WIDTH, BODY_WIDTH, MAX_HEIGHT - STANDOFF,
                        App.Vector(-BODY_WIDTH / 2, -BODY_WIDTH / 2, STANDOFF))
    for cutter in contacts + [center_metal, marker]:
        body = body.cut(cutter)
    feature("Molded_body", body, (0.07, 0.07, 0.075))
    for number, shape in enumerate(contacts, 1):
        feature(f"Terminal_{number}", shape, (0.72, 0.73, 0.76))
    feature("Center_metal_DO_NOT_SOLDER", center_metal, (0.72, 0.73, 0.76))
    feature("Pin_1_index", marker, (0.30, 0.30, 0.32))
    doc.recompute()

    bounds = App.BoundBox()
    volume = 0.0
    for obj, _ in objects:
        bounds.add(obj.Shape.BoundBox)
        volume += obj.Shape.Volume
    assert len(objects) == 11
    for actual, expected in [(bounds.XMin, -0.8), (bounds.XMax, 0.8),
                             (bounds.YMin, -0.8), (bounds.YMax, 0.8),
                             (bounds.ZMin, 0.0), (bounds.ZMax, MAX_HEIGHT)]:
        assert abs(actual - expected) < 1e-7, (actual, expected)
    Import.export(objects, str(output))
    loaded = Part.read(str(output))
    assert loaded.isValid() and len(loaded.Solids) == 11
    assert abs(loaded.Volume - volume) < 1e-7
    App.closeDocument(doc.Name)
    print(f"Saved {output}: 1.60 x 1.60 x 0.50 mm, 11 valid solids")


if __name__ == "__main__":
    build(Path(__file__).resolve().with_name(MODEL_NAME + ".step"))
