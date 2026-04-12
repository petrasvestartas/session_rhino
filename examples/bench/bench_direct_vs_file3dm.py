#! python3
"""Benchmark: direct doc.Objects.AddCurve() vs File3dm write+import.

Run in Rhino 8 Script Editor.
Both methods receive pre-built PolylineCurve objects, so this isolates
the File3dm I/O overhead from conversion costs.
"""
import System
import System.Diagnostics
import Rhino
import scriptcontext
import tempfile
import os
import random


def make_curves(n, pts_per_curve=5, seed=42):
    random.seed(seed)
    curves = []
    for _ in range(n):
        pl = Rhino.Geometry.Polyline(pts_per_curve)
        cx = random.random() * 100
        cy = random.random() * 100
        for j in range(pts_per_curve):
            pl.Add(Rhino.Geometry.Point3d(
                cx + random.random() * 10,
                cy + random.random() * 10,
                random.random() * 5,
            ))
        curves.append(Rhino.Geometry.PolylineCurve(pl))
    return curves


def bench_direct(curves):
    doc = Rhino.RhinoDoc.ActiveDoc
    guids = []
    doc.Views.RedrawEnabled = False
    sw = System.Diagnostics.Stopwatch()
    sw.Start()
    for c in curves:
        guids.append(doc.Objects.AddCurve(c))
    sw.Stop()
    doc.Views.RedrawEnabled = True
    for g in guids:
        doc.Objects.Delete(g, True)
    return sw.ElapsedMilliseconds


def bench_file3dm(curves):
    doc = Rhino.RhinoDoc.ActiveDoc
    f3dm = Rhino.FileIO.File3dm()
    for c in curves:
        f3dm.Objects.AddCurve(c)
    tmp = tempfile.mktemp(suffix=".3dm")
    sw = System.Diagnostics.Stopwatch()
    doc.Views.RedrawEnabled = False
    sw.Start()
    f3dm.Write(tmp, 8)
    scriptcontext.doc.Import(tmp)
    sw.Stop()
    doc.Views.RedrawEnabled = True
    try:
        os.remove(tmp)
    except:
        pass
    return sw.ElapsedMilliseconds


def bench_file3dm_full(curves):
    """Time everything: File3dm creation + add + write + import."""
    doc = Rhino.RhinoDoc.ActiveDoc
    sw = System.Diagnostics.Stopwatch()
    doc.Views.RedrawEnabled = False
    sw.Start()
    f3dm = Rhino.FileIO.File3dm()
    for c in curves:
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


print("=" * 60)
print("Benchmark: direct AddCurve vs File3dm write+import")
print("=" * 60)
print(f"{'N':>8} | {'direct ms':>10} | {'f3dm IO ms':>11} | {'f3dm full ms':>13} | {'ratio IO':>9}")
print("-" * 60)

for n in [1000, 5000, 10000]:
    curves = make_curves(n)
    t_direct = bench_direct(curves)
    curves = make_curves(n)
    t_f3dm = bench_file3dm(curves)
    curves = make_curves(n)
    t_f3dm_full = bench_file3dm_full(curves)
    ratio = t_f3dm / t_direct if t_direct > 0 else float("inf")
    print(f"{n:>8} | {t_direct:>10} | {t_f3dm:>11} | {t_f3dm_full:>13} | {ratio:>8.1f}x")

print()
print("direct     = doc.Objects.AddCurve() in loop")
print("f3dm IO    = File3dm.Write() + doc.Import() only (build not timed)")
print("f3dm full  = File3dm create + add + write + import (all timed)")
