#! python3
"""Benchmark: full session_rhino pipeline broken into phases.

Run in Rhino 8 Script Editor.
Times each phase of the pb → Rhino pipeline to show where time is spent:
  Phase 1: protobuf deserialization
  Phase 2: session_py → Rhino geometry conversion
  Phase 3a: add to doc (direct AddCurve)
  Phase 3b: add to doc (File3dm write+import)

Change FILEPATH below to test with different datasets.
"""
import System
import System.Diagnostics
import Rhino
import scriptcontext
import tempfile
import os

FILEPATH = r"C:\brg\code_rust\session\session_data\WoodF2F_annen.pb"


def phase1_load(filepath):
    """Deserialize protobuf into session_py objects."""
    from session_py.session import Session as PySession
    sw = System.Diagnostics.Stopwatch()
    sw.Start()
    data = PySession.pb_load(filepath)
    sw.Stop()
    return data, sw.ElapsedMilliseconds


def phase2_convert_current(polylines):
    """Convert using current rhino_polyline.to_rhino() approach."""
    from session_rhino.rhino_polyline import to_rhino
    sw = System.Diagnostics.Stopwatch()
    sw.Start()
    curves = [to_rhino(pl) for pl in polylines]
    sw.Stop()
    return curves, sw.ElapsedMilliseconds


def phase2_convert_optimized(polylines):
    """Convert using System.Array + flat coord access."""
    sw = System.Diagnostics.Stopwatch()
    sw.Start()
    curves = []
    for pl in polylines:
        n = pl.point_count()
        arr = System.Array.CreateInstance(Rhino.Geometry.Point3d, n)
        coords = pl._coords
        for i in range(n):
            j = i * 3
            arr[i] = Rhino.Geometry.Point3d(coords[j], coords[j + 1], coords[j + 2])
        curves.append(Rhino.Geometry.PolylineCurve(arr))
    sw.Stop()
    return curves, sw.ElapsedMilliseconds


def phase3_direct(curves):
    """Add to doc via doc.Objects.AddCurve()."""
    doc = Rhino.RhinoDoc.ActiveDoc
    guids = []
    doc.Views.RedrawEnabled = False
    sw = System.Diagnostics.Stopwatch()
    sw.Start()
    for c in curves:
        if c is not None:
            guids.append(doc.Objects.AddCurve(c))
    sw.Stop()
    doc.Views.RedrawEnabled = True
    for g in guids:
        doc.Objects.Delete(g, True)
    return sw.ElapsedMilliseconds


def phase3_file3dm(curves):
    """Add to doc via File3dm write+import."""
    doc = Rhino.RhinoDoc.ActiveDoc
    doc.Views.RedrawEnabled = False
    sw = System.Diagnostics.Stopwatch()
    sw.Start()
    f3dm = Rhino.FileIO.File3dm()
    for c in curves:
        if c is not None:
            f3dm.Objects.AddCurve(c)
    tmp = tempfile.mktemp(suffix=".3dm")
    f3dm.Write(tmp, 8)
    scriptcontext.doc.Import(tmp)
    sw.Stop()
    doc.Views.RedrawEnabled = True
    try:
        os.remove(tmp)
    except:
        pass
    return sw.ElapsedMilliseconds


print("=" * 65)
print(f"Full pipeline benchmark: {os.path.basename(FILEPATH)}")
print("=" * 65)

data, t_load = phase1_load(FILEPATH)
polylines = list(data.objects.polylines)
meshes = list(data.objects.meshes)
breps = list(data.objects.breps)
n_total = len(polylines) + len(meshes) + len(breps)

print(f"Objects: {len(polylines)} polylines, {len(meshes)} meshes, {len(breps)} breps ({n_total} total)")
print()

curves_cur, t_conv_cur = phase2_convert_current(polylines)
curves_opt, t_conv_opt = phase2_convert_optimized(polylines)

t_direct = phase3_direct(curves_cur)
t_f3dm = phase3_file3dm(curves_cur)

total_cur = t_load + t_conv_cur + t_f3dm
total_opt = t_load + t_conv_opt + t_direct

print(f"Phase 1  pb_load:              {t_load:>6} ms")
print(f"Phase 2  to_rhino (current):   {t_conv_cur:>6} ms")
print(f"Phase 2  to_rhino (optimized): {t_conv_opt:>6} ms  ({t_conv_cur/t_conv_opt if t_conv_opt else 0:.1f}x)")
print(f"Phase 3  add (direct):         {t_direct:>6} ms")
print(f"Phase 3  add (File3dm):        {t_f3dm:>6} ms")
print()
print(f"Total current  (load+convert+file3dm): {total_cur:>6} ms")
print(f"Total optimized (load+convert+direct): {total_opt:>6} ms  ({total_cur/total_opt if total_opt else 0:.1f}x)")
print()

if total_cur > 0:
    print("Time breakdown (current pipeline):")
    print(f"  pb_load:    {100*t_load/total_cur:>5.1f}%")
    print(f"  to_rhino:   {100*t_conv_cur/total_cur:>5.1f}%")
    print(f"  file3dm IO: {100*t_f3dm/total_cur:>5.1f}%")
