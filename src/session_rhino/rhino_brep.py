import Rhino
import System

from . import rhino_nurbscurve
from . import rhino_nurbssurface


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


def to_rhino(brep):
    """Convert session BRep to Rhino Brep with proper trim loops."""
    tol = Rhino.RhinoDoc.ActiveDoc.ModelAbsoluteTolerance
    face_breps = []
    for face in brep.m_faces:
        si = face.surface_index
        if si < 0 or si >= len(brep.m_surfaces):
            continue
        srf = brep.m_surfaces[si]

        # Collect 3D curves for each loop
        outer_curves = []
        inner_curves = []
        for li in face.loop_indices:
            if li < 0 or li >= len(brep.m_loops):
                continue
            loop = brep.m_loops[li]
            # Try actual 3D edge curves first (preserves NURBS circles)
            rcurves = _loop_to_3d_curves(brep, loop)
            if rcurves:
                rc = _join_curves(rcurves, tol)
            else:
                rc = _loop_to_3d_polyline(brep, loop, srf)
            if rc is None:
                continue
            if loop.type == 0:  # Outer
                outer_curves.append(rc)
            else:  # Inner
                inner_curves.append(rc)

        # Planar face with trims: use CreatePlanarBreps (handles holes)
        if outer_curves and srf.is_planar():
            all_curves = outer_curves + inner_curves
            planar = Rhino.Geometry.Brep.CreatePlanarBreps(all_curves, tol)
            if planar and len(planar) > 0:
                face_breps.extend(planar)
                continue

        # Non-planar or no trims: use full surface
        rsrf = rhino_nurbssurface.to_rhino(srf)
        fb = Rhino.Geometry.Brep.CreateFromSurface(rsrf)
        if fb is not None:
            face_breps.append(fb)

    if len(face_breps) > 1:
        joined = Rhino.Geometry.Brep.JoinBreps(face_breps, tol)
        if joined and len(joined) > 0:
            return list(joined)
    return face_breps


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
