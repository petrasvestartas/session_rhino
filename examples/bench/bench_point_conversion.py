#! python3
"""Benchmark: Point conversion strategies for building PolylineCurve.

Run in Rhino 8 Script Editor.
Compares three ways to convert flat [x,y,z,...] coords into PolylineCurve:
  A) current session_rhino approach (intermediate objects + Python list)
  B) System.Array.CreateInstance + direct flat-coord indexing
  C) Rhino.Geometry.Polyline() builder
"""
import System
import System.Diagnostics
import Rhino
import random


def make_flat_coords(n_polylines, pts_per_polyline, seed=42):
    random.seed(seed)
    all_coords = []
    for _ in range(n_polylines):
        coords = []
        cx = random.random() * 100
        cy = random.random() * 100
        for j in range(pts_per_polyline):
            coords.append(cx + random.random() * 10)
            coords.append(cy + random.random() * 10)
            coords.append(random.random() * 5)
        all_coords.append(coords)
    return all_coords


def method_a_current(all_coords, m):
    """Simulates current rhino_polyline.to_rhino():
    get_points() creates Point objects, then builds Point3d list."""
    curves = []
    for coords in all_coords:
        # Simulate get_points() creating intermediate tuples
        points = []
        for i in range(m):
            idx = i * 3
            p = (coords[idx], coords[idx + 1], coords[idx + 2])
            points.append(p)
        # Simulate to_rhino() building Point3d from Point objects
        pts = []
        for p in points:
            pts.append(Rhino.Geometry.Point3d(float(p[0]), float(p[1]), float(p[2])))
        curves.append(Rhino.Geometry.PolylineCurve(pts))
    return curves


def method_b_system_array(all_coords, m):
    """System.Array + direct flat-coord indexing, no intermediate objects."""
    curves = []
    for coords in all_coords:
        arr = System.Array.CreateInstance(Rhino.Geometry.Point3d, m)
        for i in range(m):
            j = i * 3
            arr[i] = Rhino.Geometry.Point3d(coords[j], coords[j + 1], coords[j + 2])
        curves.append(Rhino.Geometry.PolylineCurve(arr))
    return curves


def method_c_polyline_builder(all_coords, m):
    """Rhino.Geometry.Polyline with Add(), then wrap in PolylineCurve."""
    curves = []
    for coords in all_coords:
        pl = Rhino.Geometry.Polyline(m)
        for i in range(m):
            j = i * 3
            pl.Add(Rhino.Geometry.Point3d(coords[j], coords[j + 1], coords[j + 2]))
        curves.append(Rhino.Geometry.PolylineCurve(pl))
    return curves


def time_method(fn, all_coords, m, warmup=1, runs=3):
    for _ in range(warmup):
        fn(all_coords, m)
    best = float("inf")
    for _ in range(runs):
        sw = System.Diagnostics.Stopwatch()
        sw.Start()
        fn(all_coords, m)
        sw.Stop()
        best = min(best, sw.ElapsedMilliseconds)
    return best


N = 1000
M = 100
print("=" * 65)
print(f"Benchmark: Point conversion strategies ({N} polylines x {M} pts)")
print("=" * 65)

all_coords = make_flat_coords(N, M)

t_a = time_method(method_a_current, all_coords, M)
t_b = time_method(method_b_system_array, all_coords, M)
t_c = time_method(method_c_polyline_builder, all_coords, M)

print(f"  A) current (get_points + list):    {t_a:>6} ms")
print(f"  B) System.Array + flat coords:     {t_b:>6} ms  ({t_a/t_b if t_b else 0:.1f}x faster)")
print(f"  C) Polyline builder + flat coords: {t_c:>6} ms  ({t_a/t_c if t_c else 0:.1f}x faster)")
print()
print("Method A simulates current rhino_polyline.to_rhino():")
print("  get_points() → N Point objects → N Point3d via float(p[0])...")
print("Method B skips intermediate objects, indexes flat coords directly")
print("Method C uses Rhino.Geometry.Polyline.Add() builder")
print()

# Also test with larger polylines
for m2 in [10, 50, 500]:
    all_coords2 = make_flat_coords(N, m2)
    ta2 = time_method(method_a_current, all_coords2, m2)
    tb2 = time_method(method_b_system_array, all_coords2, m2)
    print(f"  {N}x{m2:>3} pts: A={ta2:>5}ms  B={tb2:>5}ms  speedup={ta2/tb2 if tb2 else 0:.1f}x")
