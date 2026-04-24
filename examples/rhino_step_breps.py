#! python3
# venv: session_py

from session_py.reload import reload_all
import session_rhino
reload_all()

import os
import Rhino
import System
import scriptcontext as sc

from session_py.brep import BRep
from session_rhino.rhino_brep import to_rhino

SERIALIZATION_DIR = r"C:\brg\code_rust\session\serialization"
STEM = ""        # empty = load all .pb files; or set e.g. "schoring_foot_0"
SCALE = 1000.0  # STEP data is in meters, Rhino document is in mm


def get_or_create_layer(name):
    idx = sc.doc.Layers.FindByFullPath(name, -1)
    if idx >= 0:
        return idx
    layer = Rhino.DocObjects.Layer()
    layer.Name = name
    return sc.doc.Layers.Add(layer)


def main():
    pb_files = sorted(
        f for f in os.listdir(SERIALIZATION_DIR)
        if f.startswith(STEM) and f.endswith(".pb")
    )
    if not pb_files:
        print("no .pb files found - run main_6 first")
        return

    xform = Rhino.Geometry.Transform.Scale(Rhino.Geometry.Point3d.Origin, SCALE)
    added = 0

    for pb_file in pb_files:
        path = os.path.join(SERIALIZATION_DIR, pb_file)
        name = os.path.splitext(pb_file)[0]
        brep = BRep.pb_load(path)
        srf0 = brep.m_surfaces[0] if brep.m_surfaces else None
        print("{}: faces={} srf0_valid={}".format(
            name, brep.face_count(), srf0.is_valid() if srf0 else "no_srf"))

        try:
            rbreps = to_rhino(brep)
        except Exception as e:
            print("  to_rhino error: {}".format(e))
            import traceback; traceback.print_exc()
            continue

        if not rbreps:
            print("  no geometry")
            continue

        layer_idx = get_or_create_layer(name)
        attr = Rhino.DocObjects.ObjectAttributes()
        attr.LayerIndex = layer_idx

        for rb in rbreps:
            if rb is None or not rb.IsValid:
                print("  invalid brep")
                continue
            rb.Transform(xform)
            sc.doc.Objects.AddBrep(rb, attr)
            added += 1

    sc.doc.Views.Redraw()
    print("added {} brep(s) scaled x{}".format(added, SCALE))


main()
