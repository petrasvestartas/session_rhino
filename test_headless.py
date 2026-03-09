"""Headless Rhino test: verify planar surface translation via rhino_brep.py"""
import sys
import os
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

import rhinoinside
rhinoinside.load(r"C:\Program Files\Rhino 8\System")

import Rhino  # noqa: E402
import System  # noqa: E402

from session_py.brep import BRep
from session_py.session import Session as PySession
from session_rhino import rhino_brep

TOL = 0.001


def _to_array(items, t):
    arr = System.Array.CreateInstance(t, len(items))
    for i, v in enumerate(items):
        arr[i] = v
    return arr


def check_brep_file(path):
    doc = Rhino.RhinoDoc.CreateHeadless(None)
    Rhino.RhinoDoc.ActiveDoc = doc

    with open(path) as f:
        data = json.load(f)

    brep_list = data if isinstance(data, list) else [data]
    results = []
    for bd in brep_list:
        if bd.get("type") != "BRep":
            continue
        b = BRep.__jsonload__(bd)
        rbreps = rhino_brep.to_rhino(b)
        for rb in rbreps:
            n_faces = rb.Faces.Count
            for fi in range(n_faces):
                face = rb.Faces[fi]
                is_planar, _ = face.TryGetPlane()
                srf_type = type(face.UnderlyingSurface()).__name__
                results.append({
                    "face": fi,
                    "is_planar": is_planar,
                    "srf_type": srf_type,
                })

    doc.Dispose()
    return results

def check_nurbssurface_json(path):
    """Check nurbssurfaces with outer_loop from a session JSON (rhino_session_json path)."""
    from session_rhino import rhino_session_json

    doc = Rhino.RhinoDoc.CreateHeadless(None)
    old_doc = Rhino.RhinoDoc.ActiveDoc
    Rhino.RhinoDoc.ActiveDoc = doc

    with open(path) as f:
        data = json.load(f)

    results = []
    for srf_data in data.get("objects", {}).get("nurbssurfaces", []):
        has_outer = bool(srf_data.get("outer_loop"))
        rsrf = rhino_session_json._json_to_nurbssurface(srf_data)
        tol = doc.ModelAbsoluteTolerance

        if has_outer:
            outer = rhino_session_json._eval_uv_loop_on_surface(rsrf, srf_data["outer_loop"])
            inner_loops = [
                rhino_session_json._eval_uv_loop_on_surface(rsrf, il)
                for il in srf_data.get("inner_loops", [])
            ]
            curves_3d = [c for c in [outer] + inner_loops if c is not None]
            breps = Rhino.Geometry.Brep.CreatePlanarBreps(_to_array(curves_3d, Rhino.Geometry.Curve), tol)
            created_planar = bool(breps and len(breps) > 0)
            results.append({
                "name": srf_data.get("name", "?"),
                "has_outer": True,
                "created_planar_brep": created_planar,
                "n_inner_loops": len(srf_data.get("inner_loops", [])),
            })
        else:
            results.append({
                "name": srf_data.get("name", "?"),
                "has_outer": False,
                "created_planar_brep": None,
            })

    doc.Dispose()
    Rhino.RhinoDoc.ActiveDoc = old_doc
    return results


def check_brep_is_planar_tolerance(path):
    """Check that is_planar() passes with model tolerance but may fail with 1e-12."""
    with open(path) as f:
        data = json.load(f)

    brep_list = data if isinstance(data, list) else [data]
    results = []
    for bd in brep_list:
        if bd.get("type") != "BRep":
            continue
        b = BRep.__jsonload__(bd)
        for fi, face in enumerate(b.m_faces):
            si = face.surface_index
            if si < 0 or si >= len(b.m_surfaces):
                continue
            srf = b.m_surfaces[si]
            tight = srf.is_planar()                  # default 1e-12
            loose = srf.is_planar(tolerance=TOL)     # rhino model tol
            results.append({
                "face": fi,
                "is_planar_1e12": tight,
                "is_planar_1e3": loose,
            })
    return results


def check_brep_boundary_vs_mesh(path):
    """Check that BRep outer linear boundaries match corresponding closed mesh vertices.

    For each BRep face outer loop, collect all linear (order-2) curve control
    points and verify each lies within TOL of some vertex in one of the session
    meshes.  Circle curves (order != 2) are skipped.  Returns a list of
    (brep_idx, face_idx, pt, min_dist) for any point that exceeds TOL.
    """
    import math
    data = PySession.pb_load(path)
    breps = list(data.objects.breps)
    meshes = list(data.objects.meshes)

    all_mesh_pts = []
    for mesh in meshes:
        for vk, vert in mesh.vertex.items():
            p = vert.position()
            all_mesh_pts.append((p[0], p[1], p[2]))

    def min_dist(pt):
        best = float("inf")
        for mp in all_mesh_pts:
            d = math.sqrt((pt[0]-mp[0])**2 + (pt[1]-mp[1])**2 + (pt[2]-mp[2])**2)
            if d < best:
                best = d
        return best

    mismatches = []
    for bi, brep in enumerate(breps):
        for fi, face in enumerate(brep.m_faces):
            outer_li = next((li for li in face.loop_indices
                             if brep.m_loops[li].type == 0), None)
            if outer_li is None:
                continue
            loop = brep.m_loops[outer_li]
            for ti in loop.trim_indices:
                trim = brep.m_trims[ti]
                edge = brep.m_topology_edges[trim.edge_index]
                crv = brep.m_curves_3d[edge.curve_3d_index]
                if crv.order() != 2:
                    continue
                for i in range(crv.cv_count()):
                    p = crv.get_cv(i)
                    d = min_dist(p)
                    if d > TOL:
                        mismatches.append((bi, fi, tuple(round(x, 4) for x in p), round(d, 6)))
    return mismatches


def check_brep_is_planar_headless(path):
    """Check srf.is_planar() with tight vs model tolerance for each BRep face surface."""
    data = PySession.pb_load(path)
    breps = list(data.objects.breps)
    results = []
    for bi, brep in enumerate(breps):
        for fi, face in enumerate(brep.m_faces):
            si = face.surface_index
            if si < 0 or si >= len(brep.m_surfaces):
                continue
            srf = brep.m_surfaces[si]
            tight = srf.is_planar()
            loose = srf.is_planar(tolerance=TOL)
            results.append((bi, fi, tight, loose))
    return results


def check_builder_available():
    try:
        b = Rhino.Geometry.BrepBuilder()
        return True, type(b).__name__
    except Exception as e:
        return False, str(e)


def check_session_brep_gaps(path):
    """Returns list of gap strings from check_naked_edges — empty = C++ data is clean."""
    import io
    import contextlib
    with open(path) as f:
        data = json.load(f)
    brep_list = data if isinstance(data, list) else [data]
    all_gaps = []
    for bd in brep_list:
        if bd.get("type") != "BRep":
            continue
        b = BRep.__jsonload__(bd)
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rhino_brep.check_naked_edges(b)
        gaps = [l for l in buf.getvalue().splitlines() if l]
        all_gaps.extend(gaps)
    return all_gaps


def check_rhino_naked_edges(path):
    """Count naked edges in the converted Rhino BRep — should be 0 if JoinBreps works."""
    doc = Rhino.RhinoDoc.CreateHeadless(None)
    Rhino.RhinoDoc.ActiveDoc = doc
    with open(path) as f:
        data = json.load(f)
    brep_list = data if isinstance(data, list) else [data]
    results = []
    for bd in brep_list:
        if bd.get("type") != "BRep":
            continue
        b = BRep.__jsonload__(bd)
        rbreps = rhino_brep.to_rhino(b)
        for rb in rbreps:
            naked = rb.GetNakedEdges()
            results.append(len(naked) if naked else 0)
    doc.Dispose()
    return results


if __name__ == "__main__":
    print("=== Rhino headless test ===")
    print(f"Rhino version: {Rhino.RhinoApp.Version}")

    loft_pb = "C:/pc/3_code/code_rust/session/session_data/mesh_quad_tri_loft2_out.pb"
    if os.path.exists(loft_pb):
        print("\n--- loft BRep: srf.is_planar() tight vs loose ---")
        plan_results = check_brep_is_planar_headless(loft_pb)
        tight_fail = sum(1 for _, _, t, _ in plan_results if not t)
        loose_fail = sum(1 for _, _, _, l in plan_results if not l)
        print(f"  is_planar(1e-12) fails: {tight_fail}/{len(plan_results)}")
        print(f"  is_planar({TOL}) fails: {loose_fail}/{len(plan_results)}")
        if tight_fail:
            for bi, fi, tight, loose in plan_results:
                if not tight:
                    print(f"    brep[{bi}] face[{fi}]: tight=False loose={loose}")

        print("\n--- loft BRep: boundary pts vs mesh vertices ---")
        mismatches = check_brep_boundary_vs_mesh(loft_pb)
        print(f"  boundary pts > {TOL} from any mesh vertex: {len(mismatches)}")
        for bi, fi, pt, d in mismatches[:10]:
            print(f"    brep[{bi}] face[{fi}]: {pt} dist={d}")

    test_files = {
        "brep_box":    "C:/pc/3_code/code_rust/session/session_data/brep_box.json",
        "brep_lshape": "C:/pc/3_code/code_rust/session/session_data/brep_lshape.json",
        "brep_demo":   "C:/pc/3_code/code_rust/session/session_data/brep_demo.json",
    }

    print("\n--- BrepBuilder availability ---")
    ok, msg = check_builder_available()
    print(f"  BrepBuilder: {'OK' if ok else 'UNAVAILABLE'} ({msg})")

    for label, path in test_files.items():
        if not os.path.exists(path):
            print(f"\n[SKIP] {label}: file not found")
            continue

        print(f"\n--- {label}: gap diagnostics ---")
        gaps = check_session_brep_gaps(path)
        print(f"  C++ BRep gaps: {len(gaps)} (should be 0)")
        for g in gaps[:5]:
            print(f"    {g}")
        naked = check_rhino_naked_edges(path)
        print(f"  Rhino naked edges per brep: {naked}")

        print(f"\n--- {label} ---")

        tol_results = check_brep_is_planar_tolerance(path)
        if tol_results:
            tight_fail = sum(1 for r in tol_results if not r["is_planar_1e12"])
            loose_fail = sum(1 for r in tol_results if not r["is_planar_1e3"])
            print(f"  is_planar(1e-12) fails on {tight_fail}/{len(tol_results)} faces")
            print(f"  is_planar(0.001) fails on {loose_fail}/{len(tol_results)} faces")

        brep_results = check_brep_file(path)
        if brep_results:
            plane_srf  = sum(1 for r in brep_results if r["srf_type"] == "PlaneSurface")
            nurbs_srf  = sum(1 for r in brep_results if r["srf_type"] == "NurbsSurface")
            planar_ok  = sum(1 for r in brep_results if r["is_planar"] and r["srf_type"] == "PlaneSurface")
            planar_bad = sum(1 for r in brep_results if r["is_planar"] and r["srf_type"] == "NurbsSurface")
            total = len(brep_results)
            print(f"  Rhino faces: {total} total")
            print(f"    PlaneSurface (CreatePlanarBreps) : {plane_srf}")
            print(f"    NurbsSurface (CreateFromSurface) : {nurbs_srf}")
            print(f"    planar+PlaneSurface [OK]         : {planar_ok}")
            print(f"    planar+NurbsSurface [BAD]        : {planar_bad}  <- should be 0")

    nurbs_file = "C:/pc/3_code/code_rust/session/session_data/nurbs_meshing.json"
    if os.path.exists(nurbs_file):
        print(f"\n--- nurbs_meshing (session_json path) ---")
        results = check_nurbssurface_json(nurbs_file)
        for r in results:
            if r["has_outer"]:
                status = "OK" if r["created_planar_brep"] else "FAIL"
                print(f"  {r['name']}: CreatePlanarBreps={status} (holes={r['n_inner_loops']})")
            else:
                print(f"  {r['name']}: no outer loop")
