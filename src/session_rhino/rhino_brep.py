import Rhino
import System

from . import rhino_nurbscurve
from . import rhino_nurbssurface


def check_naked_edges(brep):
    """Print max gap between adjacent face boundary segments (diagnostic)."""
    from collections import defaultdict
    seg_map = defaultdict(list)
    prec = 1e-6
    for fi, face in enumerate(brep.m_faces):
        for li in face.loop_indices:
            loop = brep.m_loops[li]
            if loop.type != 0:
                continue
            for ti in loop.trim_indices:
                trim = brep.m_trims[ti]
                edge = brep.m_topology_edges[trim.edge_index]
                crv = brep.m_curves_3d[edge.curve_3d_index]
                if crv.order() != 2:
                    continue
                n = crv.cv_count() - 1
                for i in range(n):
                    p0 = crv.get_cv(i)
                    p1 = crv.get_cv(i + 1)
                    k = (round(min(p0[0], p1[0]) / prec), round(min(p0[1], p1[1]) / prec),
                         round(max(p0[0], p1[0]) / prec), round(max(p0[1], p1[1]) / prec))
                    seg_map[k].append((fi, p0, p1))
    for k, segs in seg_map.items():
        if len(segs) == 2:
            (_, a0, a1), (_, b0, b1) = segs
            d = max(abs(a0[0] - b0[0]), abs(a0[1] - b0[1]), abs(a0[2] - b0[2]))
            if d > 1e-10:
                print(f"gap {d:.6f} at {k}")


def _build_with_builder(brep):
    try:
        b = Rhino.Geometry.BrepBuilder()
    except Exception:
        return None
    doc_tol = Rhino.RhinoDoc.ActiveDoc.ModelAbsoluteTolerance

    # 1. Surfaces
    srf_ids = []
    for srf in brep.m_surfaces:
        rsrf = rhino_nurbssurface.to_rhino(srf)
        srf_ids.append(b.AddSurface(rsrf) if rsrf else -1)

    # 2. Vertex dedup (snap to grid)
    prec = 1e-6
    vert_ids = {}

    def add_vert(x, y, z):
        k = (round(x / prec), round(y / prec), round(z / prec))
        if k not in vert_ids:
            vert_ids[k] = b.AddBrepVertex(Rhino.Geometry.Point3d(x, y, z), doc_tol)
        return vert_ids[k]

    # 3. Edge dedup: canonical key = (min_vid, max_vid)
    edge_ids = {}

    def add_edge(x0, y0, z0, x1, y1, z1):
        v0 = add_vert(x0, y0, z0)
        v1 = add_vert(x1, y1, z1)
        key = (min(v0, v1), max(v0, v1))
        if key not in edge_ids:
            line = Rhino.Geometry.LineCurve(
                Rhino.Geometry.Point3d(x0, y0, z0),
                Rhino.Geometry.Point3d(x1, y1, z1))
            ei = b.AddEdge(v0, v1, line, doc_tol)
            edge_ids[key] = (ei, v0, v1)
        ei, ev0, ev1 = edge_ids[key]
        return ei, (ev0 != v0)

    # 4. Faces
    face_colors = []
    for face in brep.m_faces:
        si = face.surface_index
        if si < 0 or si >= len(srf_ids) or srf_ids[si] < 0:
            continue
        b.AddFace(srf_ids[si], bool(face.reversed))
        face_colors.append(face.facecolor)

        for li in face.loop_indices:
            if li < 0 or li >= len(brep.m_loops):
                continue
            loop = brep.m_loops[li]
            lt = (Rhino.Geometry.BrepLoopType.Outer if loop.type == 0
                  else Rhino.Geometry.BrepLoopType.Inner)
            b.AddLoop(lt)

            for ti in loop.trim_indices:
                if ti < 0 or ti >= len(brep.m_trims):
                    continue
                trim = brep.m_trims[ti]
                edge = brep.m_topology_edges[trim.edge_index]
                crv3d = brep.m_curves_3d[edge.curve_3d_index]
                crv2d = brep.m_curves_2d[trim.curve_2d_index]
                n = crv3d.cv_count() - 1

                if crv3d.order() == 2 and n >= 2:
                    # Linear boundary — decompose into N segments
                    pts3 = [crv3d.get_cv(i) for i in range(n + 1)]
                    pts2 = [crv2d.get_cv(i) for i in range(n + 1)]
                    if trim.reversed:
                        pts3 = list(reversed(pts3))
                        pts2 = list(reversed(pts2))
                    for i in range(n):
                        p0, p1 = pts3[i], pts3[i + 1]
                        u0, u1 = pts2[i], pts2[i + 1]
                        ei, rev = add_edge(p0[0], p0[1], p0[2], p1[0], p1[1], p1[2])
                        seg2d = Rhino.Geometry.LineCurve(
                            Rhino.Geometry.Point3d(u0[0], u0[1], 0),
                            Rhino.Geometry.Point3d(u1[0], u1[1], 0))
                        b.AddTrim(ei, rev, Rhino.Geometry.Interval(0, 1), seg2d)
                else:
                    # Non-linear boundary (circle hole) — single closed edge
                    r3d = rhino_nurbscurve.to_rhino(crv3d)
                    r2d = rhino_nurbscurve.to_rhino(crv2d)
                    ps = crv3d.get_cv(0)
                    vs = add_vert(ps[0], ps[1], ps[2])
                    ei = b.AddEdge(vs, vs, r3d, doc_tol)
                    dom = Rhino.Geometry.Interval(
                        crv3d.knot(0), crv3d.knot(crv3d.knot_count() - 1))
                    b.AddTrim(ei, bool(trim.reversed), dom, r2d)

    result = b.GetResult()
    if result is None:
        return None
    for i, fc in enumerate(face_colors):
        if fc is not None and i < result.Faces.Count:
            result.Faces[i].PerFaceColor = System.Drawing.Color.FromArgb(fc.a, fc.r, fc.g, fc.b)
    return result


def _loop_to_3d_curves(brep, loop):
    """Get Rhino NurbsCurves for a loop from 3D edge curves."""
    curves = []
    for ti in loop.trim_indices:
        if ti < 0 or ti >= len(brep.m_trims):
            continue
        trim = brep.m_trims[ti]
        ei = trim.edge_index
        if ei < 0 or ei >= len(brep.m_topology_edges):
            continue
        edge = brep.m_topology_edges[ei]
        ci = edge.curve_3d_index
        if ci < 0 or ci >= len(brep.m_curves_3d):
            continue
        crv3d = brep.m_curves_3d[ci]
        rc = rhino_nurbscurve.to_rhino(crv3d)
        if rc is not None and rc.IsValid:
            if trim.reversed:
                rc.Reverse()
            curves.append(rc)
    return curves


def _loop_to_3d_polyline(brep, loop, srf):
    """Fallback: evaluate 2D trims on surface to get 3D polyline."""
    pts_3d = []
    for ti in loop.trim_indices:
        if ti < 0 or ti >= len(brep.m_trims):
            continue
        trim = brep.m_trims[ti]
        if trim.curve_2d_index < 0 or trim.curve_2d_index >= len(brep.m_curves_2d):
            continue
        crv2d = brep.m_curves_2d[trim.curve_2d_index]
        pts, _ = crv2d.divide_by_count(max(crv2d.cv_count() * 4, 16))
        for k in range(len(pts) - 1):
            p3d = srf.point_at(pts[k][0], pts[k][1])
            if p3d is not None:
                pts_3d.append(Rhino.Geometry.Point3d(p3d[0], p3d[1], p3d[2]))
    if len(pts_3d) < 3:
        return None
    pts_3d.append(pts_3d[0])
    return Rhino.Geometry.PolylineCurve(pts_3d)


def _join_curves(curves, tol):
    """Join multiple curves into one. Returns single curve or None."""
    if len(curves) == 1:
        return curves[0]
    joined = Rhino.Geometry.Curve.JoinCurves(curves, tol)
    if joined and len(joined) > 0:
        return joined[0]
    return None


def _build_with_createplanar(brep):
    """Fallback: CreatePlanarBreps + JoinBreps path."""
    doc_tol = Rhino.RhinoDoc.ActiveDoc.ModelAbsoluteTolerance
    join_tol = 1e-3
    face_breps = []
    face_colors = []
    for face in brep.m_faces:
        fc = face.facecolor
        si = face.surface_index
        if si < 0 or si >= len(brep.m_surfaces):
            continue
        srf = brep.m_surfaces[si]

        outer_curves = []
        inner_curves = []
        for li in face.loop_indices:
            if li < 0 or li >= len(brep.m_loops):
                continue
            loop = brep.m_loops[li]
            rcurves = _loop_to_3d_curves(brep, loop)
            if rcurves:
                rc = _join_curves(rcurves, join_tol)
            else:
                rc = _loop_to_3d_polyline(brep, loop, srf)
            if rc is None:
                continue
            if loop.type == 0:
                outer_curves.append(rc)
            else:
                inner_curves.append(rc)

        if outer_curves and srf.is_planar(tolerance=doc_tol):
            all_curves = outer_curves + inner_curves
            planar = Rhino.Geometry.Brep.CreatePlanarBreps(all_curves, doc_tol)
            if planar and len(planar) > 0:
                for pb in planar:
                    face_breps.append(pb)
                    face_colors.append(fc)
                continue

        rsrf = rhino_nurbssurface.to_rhino(srf)
        fb = Rhino.Geometry.Brep.CreateFromSurface(rsrf)
        if fb is not None:
            face_breps.append(fb)
            face_colors.append(fc)

    for fb, fc in zip(face_breps, face_colors):
        if fc is not None:
            fb.Faces[0].PerFaceColor = System.Drawing.Color.FromArgb(fc.a, fc.r, fc.g, fc.b)

    if len(face_breps) > 1:
        joined = Rhino.Geometry.Brep.JoinBreps(face_breps, doc_tol * 10)
        if joined and len(joined) > 0:
            return list(joined)
    return face_breps


def to_rhino(brep):
    """Convert session BRep to Rhino Brep with proper trim loops."""
    result = _build_with_builder(brep)
    if result is not None and result.IsValid:
        return [result]
    return _build_with_createplanar(brep)


def add(obj_or_list, layer_idx=0, **kwargs):
    if not isinstance(obj_or_list, list):
        obj_or_list = [obj_or_list]
    guids = []
    doc = Rhino.RhinoDoc.ActiveDoc
    for brep in obj_or_list:
        rbreps = to_rhino(brep)
        c = brep.surfacecolor
        attr = Rhino.DocObjects.ObjectAttributes()
        attr.LayerIndex = layer_idx
        if c.r or c.g or c.b:
            attr.ObjectColor = System.Drawing.Color.FromArgb(int(c.a), int(c.r), int(c.g), int(c.b))
            attr.ColorSource = Rhino.DocObjects.ObjectColorSource.ColorFromObject
        for rb in rbreps:
            guid = doc.Objects.AddBrep(rb, attr)
            if guid != System.Guid.Empty:
                guids.append(guid)
    return guids
