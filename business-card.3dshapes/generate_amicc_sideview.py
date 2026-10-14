"""Build the project-owned Amicc A-SP192SS1C-C01-3C side-view LED STEP.

Source: Amicc ADE-192S-007 V1, 17 Apr 2014, package and land drawings p7:
https://wmsc.lcsc.com/wmsc/upload/file/pdf/v2/lcsc/2210091830_Amicc-A-SP192SS1C-C01-3C_C5179642.pdf

Run: PYTHONPATH=/usr/lib/freecad-python3/lib /usr/bin/python3 generate_amicc_sideview.py

Envelope: 1.60 x 0.60 x 0.30 mm (height tolerance +/-0.05 mm).
Origin: complete body center in XY, seating surface Z=0. Footprint light
direction is -Y; STEP +Y maps to KiCad footprint -Y at zero model rotation.
Cathode/pin 2 is X<0, anode/pin 1 X>0. Substrate depth is 0.28 mm;
the lens projects 0.32 mm horizontally, with a 1.10 mm wide base.

Symbol, footprint, and STEP were independently drawn from manufacturer
dimensions; no third-party ECAD geometry was copied.
The lens taper (1.00 mm front width), metal thickness, die, and cathode mark
are visual approximations; their details are not dimensioned by Amicc.
Nominal geometry is not a worst-case tolerance envelope or optical model.
"""

from pathlib import Path

import FreeCAD as App
import Part
import Import

MODEL_NAME = "Amicc_A-SP192SS1C-C01-3C_SideView"


def box(x, y, z, dx, dy, dz):
    return Part.makeBox(dx, dy, dz, App.Vector(x, y, z))


def build(output):
    doc = App.newDocument("Amicc_side_view_LED")
    objects = []

    def feature(name, shape, color):
        shape = shape.removeSplitter()
        assert shape.isValid() and len(shape.Solids) == 1, name
        obj = doc.addObject("Part::Feature", name)
        obj.Label = name
        obj.Shape = shape
        objects.append((obj, [color] * len(shape.Faces)))
        return obj

    substrate = box(-0.8, -0.3, 0, 1.6, 0.28, 0.3)
    terminals = []
    for x in (-0.8, 0.4):
        # A thin wrap over both ends; all metal stays inside nominal envelope.
        bottom = box(x, -0.3, 0, 0.4, 0.28, 0.015)
        top = box(x, -0.3, 0.285, 0.4, 0.28, 0.015)
        end_x = -0.8 if x < 0 else 0.785
        end = box(end_x, -0.3, 0, 0.015, 0.28, 0.3)
        terminal = bottom.fuse(top).fuse(end).removeSplitter()
        terminals.append(terminal)
        substrate = substrate.cut(terminal)

    marker = box(-0.28, -0.3, 0.03, 0.18, 0.005, 0.24)
    substrate = substrate.cut(marker)
    points = [App.Vector(-0.55, -0.02, 0), App.Vector(0.55, -0.02, 0),
              App.Vector(0.5, 0.3, 0), App.Vector(-0.5, 0.3, 0)]
    lens = Part.Face(Part.makePolygon(points + [points[0]])).extrude(App.Vector(0, 0, 0.3))
    die = box(-0.06, -0.005, 0.09, 0.12, 0.035, 0.12)
    lens = lens.cut(die)

    feature("Substrate", substrate, (0.86, 0.83, 0.69))
    feature("Terminal_2_cathode", terminals[0], (0.78, 0.66, 0.38))
    feature("Terminal_1_anode", terminals[1], (0.78, 0.66, 0.38))
    feature("Cathode_mark", marker, (0.08, 0.36, 0.10))
    feature("Orange_LED_die", die, (1.0, 0.34, 0.015))
    feature("Water_clear_lens", lens, (0.96, 0.97, 1.0, 0.25))
    doc.recompute()

    expected = (-0.8, 0.8, -0.3, 0.3, 0.0, 0.3)
    bounds = App.BoundBox()
    volume = 0.0
    for i, (obj, _) in enumerate(objects):
        bounds.add(obj.Shape.BoundBox)
        volume += obj.Shape.Volume
        for other, _ in objects[i + 1:]:
            assert obj.Shape.common(other.Shape).Volume < 1e-9, (obj.Label, other.Label)
    actual = (bounds.XMin, bounds.XMax, bounds.YMin, bounds.YMax, bounds.ZMin, bounds.ZMax)
    assert all(abs(a - b) < 1e-7 for a, b in zip(actual, expected)), actual
    assert all(abs(t.BoundBox.ZMin) < 1e-7 for t in terminals)

    Import.export(objects, str(output))
    loaded = Part.read(str(output))
    assert loaded.isValid() and len(loaded.Solids) == 6
    assert abs(loaded.Volume - volume) < 1e-7
    bounds = loaded.BoundBox
    actual = (bounds.XMin, bounds.XMax, bounds.YMin, bounds.YMax, bounds.ZMin, bounds.ZMax)
    assert all(abs(a - b) < 1e-7 for a, b in zip(actual, expected)), actual
    assert "SURFACE_STYLE_TRANSPARENT" in output.read_text()
    App.closeDocument(doc.Name)
    print(f"Saved {output}: 1.60 x 0.60 x 0.30 mm, 6 valid nonoverlapping solids")
    print("Seating plane Z=0; light +Y in STEP / -Y in KiCad; pin 1=A right, pin 2=K left")


if __name__ == "__main__":
    build(Path(__file__).resolve().with_name(MODEL_NAME + ".step"))
