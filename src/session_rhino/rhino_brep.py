import Rhino
import System

from . import rhino_nurbscurve
from . import rhino_nurbssurface

_FORWARD = 0
_REVERSED = 1


def check_naked_edges(brep):
    """Print every non-degenerated edge that is not shared by exactly two face uses (diagnostic)."""
    for ei, edge in enumerate(brep.m_edges):
        if edge.degenerated:
            continue
        uses = brep.edge_faces(ei)
        if len(uses) != 2:
            print(f"edge {ei}: {len(uses)} face use(s)")


def _build_with_builder(brep):
    """Rhino BrepBuilder from the OCCT-style tables: one Rhino vertex/edge per BRep vertex/edge,
    face same_sense from the shell orientation, wires as loops (first = outer), pcurves flipped
    into loop-traversal direction for reversed edge uses. Degenerated edges (poles/apices) have
    no 3D curve and are skipped; a face that needs them falls back to the surface path."""
    try:
        b = Rhino.Geometry.BrepBuilder()
    except Exception:
        return None
    doc_tol = Rhino.RhinoDoc.ActiveDoc.ModelAbsoluteTolerance

    srf_ids = []
    for srf in brep.m_surfaces:
        rsrf = rhino_nurbssurface.to_rhino(srf)
        srf_ids.append(b.AddSurface(rsrf) if rsrf else -1)

    vert_ids = []
    for v in brep.m_vertices:
        vert_ids.append(b.AddBrepVertex(Rhino.Geometry.Point3d(v.point[0], v.point[1], v.point[2]), doc_tol))

    edge_ids = []
    for edge in brep.m_edges:
        if edge.degenerated:
            edge_ids.append(-1)
            continue
        r3d = rhino_nurbscurve.to_rhino(brep.m_curves_3d[edge.curve_3d_index])
        edge_ids.append(b.AddEdge(vert_ids[edge.start_vertex], vert_ids[edge.end_vertex], r3d, doc_tol))

    face_colors = []
    for fi, face in enumerate(brep.m_faces):
        si = face.surface_index
        if si < 0 or si >= len(srf_ids) or srf_ids[si] < 0:
            continue
        b.AddFace(srf_ids[si], brep.face_orientation(fi) == _REVERSED)
        face_colors.append(face.facecolor)

        for wi, wr in enumerate(face.wires):
            b.AddLoop(Rhino.Geometry.BrepLoopType.Outer if wi == 0 else Rhino.Geometry.BrepLoopType.Inner)
            for er in brep.wire_edges(wr):
                if edge_ids[er.index] < 0:
                    continue
                ci = brep.pcurve_index(er.index, fi, er.orientation)
                if ci < 0:
                    continue
                crv2d = brep.m_curves_2d[ci]
                r2d = rhino_nurbscurve.to_rhino(crv2d)
                rev = er.orientation == _REVERSED
                if rev:
                    r2d.Reverse()
                dom = Rhino.Geometry.Interval(crv2d.nurbsknot(0), crv2d.nurbsknot(crv2d.nurbsknot_count() - 1))
                b.AddTrim(edge_ids[er.index], rev, dom, r2d)

    result = b.GetResult()
    if result is None:
        return None
    for i, fc in enumerate(face_colors):
        if fc is not None and i < result.Faces.Count:
            result.Faces[i].PerFaceColor = System.Drawing.Color.FromArgb(fc.a, fc.r, fc.g, fc.b)
    return result


def _wire_to_3d_curves(brep, wire):
    """Rhino NurbsCurves of a wire from its 3D edge curves, in traversal direction."""
    curves = []
    for er in brep.wire_edges(wire):
        edge = brep.m_edges[er.index]
        if edge.degenerated:
            continue
        rc = rhino_nurbscurve.to_rhino(brep.m_curves_3d[edge.curve_3d_index])
        if rc is not None and rc.IsValid:
            if er.orientation == _REVERSED:
                rc.Reverse()
            curves.append(rc)
    return curves


def _wire_to_3d_polyline(brep, fi, wire, srf):
    """Fallback: evaluate the wire's pcurves on the surface to get a 3D polyline."""
    pts_3d = []
    for er in brep.wire_edges(wire):
        ci = brep.pcurve_index(er.index, fi, er.orientation)
        if ci < 0:
            continue
        crv2d = brep.m_curves_2d[ci]
        pts, _ = crv2d.divide_by_count(max(crv2d.cv_count() * 4, 16))
        if er.orientation == _REVERSED:
            pts = list(reversed(pts))
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
    arr = System.Array[Rhino.Geometry.Curve](curves)
    joined = Rhino.Geometry.Curve.JoinCurves(arr, tol)
    if joined and len(joined) > 0:
        return joined[0]
    return None


def _build_with_createplanar(brep):
    """Fallback: CreatePlanarBreps + JoinBreps path."""
    doc_tol = Rhino.RhinoDoc.ActiveDoc.ModelAbsoluteTolerance
    join_tol = 1e-3
    face_breps = []
    face_colors = []
    for fi, face in enumerate(brep.m_faces):
        fc = face.facecolor
        si = face.surface_index
        if si < 0 or si >= len(brep.m_surfaces):
            continue
        srf = brep.m_surfaces[si]

        outer_curves = []
        inner_curves = []
        for wi, wr in enumerate(face.wires):
            rcurves = _wire_to_3d_curves(brep, wr)
            if rcurves:
                rc = _join_curves(rcurves, join_tol)
            else:
                rc = _wire_to_3d_polyline(brep, fi, wr, srf)
            if rc is None:
                continue
            if wi == 0:
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
