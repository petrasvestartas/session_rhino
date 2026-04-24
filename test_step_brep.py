"""Headless test: STEP pb -> Rhino BRep. Run with Rhino's Python."""
import sys
sys.path.insert(0, r"C:\brg\code_rust\session\session_py\src")
sys.path.insert(0, r"C:\brg\code_rust\session\session_rhino\src")

import rhinoinside
rhinoinside.load(r"C:\Program Files\Rhino 8\System")

import Rhino
import Rhino.FileIO

doc = Rhino.RhinoDoc.CreateHeadless(None)
Rhino.RhinoDoc.ActiveDoc = doc

from session_py.brep import BRep
from session_rhino.rhino_brep import _build_with_builder, _build_with_createplanar, to_rhino

PB = r"C:\brg\code_rust\session\serialization\schoring_body_end_0_0.pb"
OUT = r"C:\brg\code_rust\session\session_rhino\test_step_result.3dm"

brep = BRep.pb_load(PB)
print("BRep: faces=%d edges=%d verts=%d" % (brep.face_count(), brep.edge_count(), brep.vertex_count()))
print("trims: total=%d  reversed=%d  forward=%d" % (
    len(brep.m_trims),
    sum(1 for t in brep.m_trims if t.reversed),
    sum(1 for t in brep.m_trims if not t.reversed)))

# ---- test _build_with_builder ----
print("\n-- _build_with_builder --")
try:
    result = _build_with_builder(brep)
    if result is None:
        print("  returned None")
    else:
        print("  IsValid=%s  Faces=%d  NakedEdges=%d" % (
            result.IsValid,
            result.Faces.Count,
            sum(1 for e in result.Edges if e.Valence == Rhino.Geometry.EdgeAdjacency.Naked)))
except Exception as e:
    print("  EXCEPTION: %s" % e)
    result = None

# ---- test to_rhino (full path) ----
print("\n-- to_rhino (builder->createplanar fallback) --")
try:
    rbreps = to_rhino(brep)
    print("  returned %d brep(s)" % len(rbreps))
    for i, rb in enumerate(rbreps):
        if rb is None:
            print("  [%d] None" % i)
        else:
            naked = sum(1 for e in rb.Edges if e.Valence == Rhino.Geometry.EdgeAdjacency.Naked)
            print("  [%d] IsValid=%s  Faces=%d  NakedEdges=%d" % (i, rb.IsValid, rb.Faces.Count, naked))
except Exception as e:
    print("  EXCEPTION: %s" % e)
    rbreps = []

# ---- scale and save ----
xform = Rhino.Geometry.Transform.Scale(Rhino.Geometry.Point3d.Origin, 1000.0)
saved = 0
for rb in rbreps:
    if rb and rb.IsValid:
        rb.Transform(xform)
        doc.Objects.AddBrep(rb)
        saved += 1

if saved:
    f3dm = Rhino.FileIO.File3dm()
    for obj in doc.Objects:
        f3dm.Objects.AddBrep(obj.Geometry)
    f3dm.Write(OUT, 8)
    print("\nSaved %d brep(s) to %s" % (saved, OUT))

doc.Dispose()
