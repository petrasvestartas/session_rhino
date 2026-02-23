"""rhino_export_csg.py
Run in Rhino: Tools > PythonScript > RunPythonScript (or EditPythonScript)
Creates CSG boolean solids and exports them to session JSON format.
- Shape 1: cube (10x10x10) minus sphere (r=6.5)
- Shape 2: cube (10x10x10) minus two cylinders at 90° to each other
"""
import json
import uuid
import Rhino
import Rhino.Geometry as rg


def _guid():
    return str(uuid.uuid4())


def _xform_identity():
    return [[1.0, 0.0, 0.0, 0.0],
            [0.0, 1.0, 0.0, 0.0],
            [0.0, 0.0, 1.0, 0.0],
            [0.0, 0.0, 0.0, 1.0]]


def _default_color():
    return {"a": 255, "b": 0, "g": 0, "r": 0}


def _nurbs_curve_json(nc, dim=3, name="crv"):
    """Convert Rhino NurbsCurve to session NurbsCurve JSON."""
    order = nc.Order
    cv_count = nc.Points.Count
    is_rat = nc.IsRational
    knots = [nc.Knots[i] for i in range(nc.Knots.Count)]
    cps = []
    for i in range(cv_count):
        pt = nc.Points.GetPoint4d(i)
        if is_rat:
            cps.append([pt.X, pt.Y, pt.Z, pt.W])   # homogeneous
        else:
            w = pt.W if pt.W != 0.0 else 1.0
            cps.append([pt.X / w, pt.Y / w, pt.Z / w])
    return {
        "control_points": cps,
        "cv_count": cv_count,
        "cv_stride": (dim + 1) if is_rat else dim,
        "dimension": dim,
        "guid": _guid(),
        "is_rational": is_rat,
        "knots": knots,
        "linecolors": [],
        "name": name,
        "order": order,
        "pointcolors": [],
        "type": "NurbsCurve",
        "width": 1.0,
        "xform": _xform_identity(),
    }


def _nurbs_surface_json(ns, name="srf"):
    """Convert Rhino NurbsSurface to session NurbsSurface JSON."""
    order_u = ns.OrderU
    order_v = ns.OrderV
    cv_u = ns.Points.CountU
    cv_v = ns.Points.CountV
    is_rat = ns.IsRational
    knots_u = [ns.KnotsU[i] for i in range(ns.KnotsU.Count)]
    knots_v = [ns.KnotsV[i] for i in range(ns.KnotsV.Count)]
    # Flat row-major: for rational stores [x*w, y*w, z*w, w], else [x, y, z]
    cps = []
    for i in range(cv_u):
        for j in range(cv_v):
            pt = ns.Points.GetPoint4d(i, j)
            if is_rat:
                cps.extend([pt.X, pt.Y, pt.Z, pt.W])
            else:
                w = pt.W if pt.W != 0.0 else 1.0
                cps.extend([pt.X / w, pt.Y / w, pt.Z / w])
    return {
        "control_points": cps,
        "cv_count_u": cv_u,
        "cv_count_v": cv_v,
        "dimension": 3,
        "facecolors": [],
        "guid": _guid(),
        "is_rational": is_rat,
        "knots_u": knots_u,
        "knots_v": knots_v,
        "linecolors": [],
        "name": name,
        "order_u": order_u,
        "order_v": order_v,
        "pointcolors": [],
        "type": "NurbsSurface",
        "width": 1.0,
        "xform": _xform_identity(),
    }


def _trim_type_str(t):
    tt = t.TrimType
    if tt == rg.BrepTrimType.Boundary:      return "Boundary"
    if tt == rg.BrepTrimType.Seam:          return "Seam"
    if tt == rg.BrepTrimType.Singular:      return "Singular"
    if tt == rg.BrepTrimType.CurveOnSurface: return "CurveOnSurface"
    return "Unknown"


def _loop_type_str(l):
    lt = l.LoopType
    if lt == rg.BrepLoopType.Outer: return "Outer"
    if lt == rg.BrepLoopType.Inner: return "Inner"
    return "Unknown"


def rhino_brep_to_json(rb, name):
    """Convert a Rhino Brep to session BRep JSON dict."""
    # Surfaces: one per Rhino surface (faces share by surface index)
    surfaces = []
    for si in range(rb.Surfaces.Count):
        ns = rb.Surfaces[si].ToNurbsSurface()
        surfaces.append(_nurbs_surface_json(ns, name="{}_s{}".format(name, si)))

    # 3D edge curves
    curves_3d = []
    for ei in range(rb.Edges.Count):
        nc = rb.Edges[ei].ToNurbsCurve()
        if nc is None:
            vs = rb.Edges[ei].StartVertex.Location
            ve = rb.Edges[ei].EndVertex.Location
            nc = rg.NurbsCurve.CreateFromLine(rg.Line(vs, ve))
        curves_3d.append(_nurbs_curve_json(nc, dim=3, name="{}_e{}".format(name, ei)))

    # 2D trim curves (one per trim, in trim index order)
    curves_2d = []
    for ti in range(rb.Trims.Count):
        trim = rb.Trims[ti]
        nc2 = trim.TrimCurve.ToNurbsCurve() if trim.TrimCurve else None
        if nc2 is None:
            # Degenerate/singular trim: zero-length line at a UV point
            dom = trim.Domain
            nc2 = rg.NurbsCurve.CreateFromLine(rg.Line(
                rg.Point3d(dom.Min, 0, 0), rg.Point3d(dom.Max, 0, 0)))
        curves_2d.append(_nurbs_curve_json(nc2, dim=2, name="{}_t{}".format(name, ti)))

    # Vertices
    vertices = []
    for vi in range(rb.Vertices.Count):
        pt = rb.Vertices[vi].Location
        vertices.append([pt.X, pt.Y, pt.Z])

    topology_vertices = []
    for vi in range(rb.Vertices.Count):
        v = rb.Vertices[vi]
        topology_vertices.append({
            "edge_indices": list(v.EdgeIndices()),
            "point_index": vi,
        })

    topology_edges = []
    for ei in range(rb.Edges.Count):
        edge = rb.Edges[ei]
        topology_edges.append({
            "curve_3d_index": ei,
            "end_vertex": edge.EndVertex.VertexIndex,
            "start_vertex": edge.StartVertex.VertexIndex,
            "trim_indices": list(edge.TrimIndices()),
        })

    faces = []
    for fi in range(rb.Faces.Count):
        face = rb.Faces[fi]
        loop_idxs = [face.Loops[k].LoopIndex for k in range(face.Loops.Count)]
        faces.append({
            "loop_indices": loop_idxs,
            "reversed": face.OrientationIsReversed,
            "surface_index": face.SurfaceIndex,
        })

    loops = []
    for li in range(rb.Loops.Count):
        loop = rb.Loops[li]
        trim_idxs = [loop.Trims[k].TrimIndex for k in range(loop.Trims.Count)]
        loops.append({
            "face_index": loop.Face.FaceIndex,
            "trim_indices": trim_idxs,
            "type": _loop_type_str(loop),
        })

    trims = []
    for ti in range(rb.Trims.Count):
        trim = rb.Trims[ti]
        ei = trim.Edge.EdgeIndex if trim.Edge is not None else -1
        trims.append({
            "curve_2d_index": ti,
            "edge_index": ei,
            "loop_index": trim.Loop.LoopIndex,
            "reversed": trim.IsReversed,
            "type": _trim_type_str(trim),
        })

    return {
        "curves_2d": curves_2d,
        "curves_3d": curves_3d,
        "faces": faces,
        "guid": _guid(),
        "loops": loops,
        "name": name,
        "surfaces": surfaces,
        "surfacecolor": _default_color(),
        "topology_edges": topology_edges,
        "topology_vertices": topology_vertices,
        "trims": trims,
        "type": "BRep",
        "vertices": vertices,
        "width": 1.0,
        "xform": _xform_identity(),
    }


def create_shapes(tol):
    results = []

    # Shape 1: 10x10x10 cube minus sphere (r=6.5, pokes through all 6 faces)
    box1 = rg.Box(rg.BoundingBox(-5, -5, -5, 5, 5, 5)).ToBrep()
    sphere = rg.Sphere(rg.Point3d(0, 0, 0), 6.5).ToBrep()
    diff1 = rg.Brep.CreateBooleanDifference([box1], [sphere], tol)
    if diff1 and len(diff1) > 0:
        results.append((diff1[0], "cube_minus_sphere"))

    # Shape 2: 10x10x10 cube minus two cylinders at 90° to each other
    # Cylinder 1: r=2.5, along Z axis
    cyl1_plane = rg.Plane(rg.Point3d(0, 0, 0), rg.Vector3d.ZAxis)
    cyl1 = rg.Cylinder(rg.Circle(cyl1_plane, 2.5), 12).ToBrep(True, True)
    # Cylinder 2: r=2.0, along X axis (perpendicular)
    cyl2_plane = rg.Plane(rg.Point3d(0, 0, 0), rg.Vector3d.XAxis)
    cyl2 = rg.Cylinder(rg.Circle(cyl2_plane, 2.0), 12).ToBrep(True, True)
    box2 = rg.Box(rg.BoundingBox(-5, -5, -5, 5, 5, 5)).ToBrep()
    diff2 = rg.Brep.CreateBooleanDifference([box2], [cyl1, cyl2], tol)
    if diff2 and len(diff2) > 0:
        results.append((diff2[0], "cube_minus_two_cylinders"))

    return results


def main():
    doc = Rhino.RhinoDoc.ActiveDoc
    tol = doc.ModelAbsoluteTolerance

    shapes = create_shapes(tol)
    if not shapes:
        print("Boolean operations failed — check tolerance or geometry")
        return

    brep_jsons = []
    for rb, name in shapes:
        j = rhino_brep_to_json(rb, name)
        brep_jsons.append(j)
        print("{}: {} faces, {} edges, {} surfaces".format(
            name, len(j["faces"]), len(j["topology_edges"]), len(j["surfaces"])))

    session = {
        "breps": brep_jsons,
        "curves": [],
        "lines": [],
        "meshes": [],
        "name": "csg_examples",
        "planes": [],
        "pointclouds": [],
        "points": [],
        "polylines": [],
        "surfaces": [],
    }

    out = "C:/pc/3_code/code_rust/session/session_data/csg_examples.json"
    with open(out, "w") as f:
        json.dump(session, f, indent=2)
    print("Saved {} BReps to {}".format(len(brep_jsons), out))


main()
