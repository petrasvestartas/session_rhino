import Rhino
import System
import json


def _set_color(doc, guid, r, g, b):
    obj = doc.Objects.Find(guid)
    if obj is None:
        return
    attr = obj.Attributes
    attr.ObjectColor = System.Drawing.Color.FromArgb(int(r), int(g), int(b))
    attr.ColorSource = Rhino.DocObjects.ObjectColorSource.ColorFromObject
    doc.Objects.ModifyAttributes(guid, attr, True)


def _json_to_mesh(data):
    rmesh = Rhino.Geometry.Mesh()
    vertex_data = data.get("vertex", {})
    for k in sorted(vertex_data.keys(), key=int):
        v = vertex_data[k]
        rmesh.Vertices.Add(v["x"], v["y"], v["z"])
    face_data = data.get("face", {})
    for k in sorted(face_data.keys(), key=int):
        f = face_data[k]
        if len(f) == 3:
            rmesh.Faces.AddFace(f[0], f[1], f[2])
        elif len(f) == 4:
            rmesh.Faces.AddFace(f[0], f[1], f[2], f[3])
    rmesh.Normals.ComputeNormals()
    rmesh.Compact()
    return rmesh


def _json_to_nurbscurve(data):
    cps = data["control_points"]
    order = data["order"]
    knots = data["knots"]
    is_rat = data.get("is_rational", False)
    n = len(cps)
    if n < 2:
        return None
    nc = Rhino.Geometry.NurbsCurve(3, is_rat, order, n)
    for i, cp in enumerate(cps):
        nc.Points.SetPoint(i, Rhino.Geometry.Point3d(cp[0], cp[1], cp[2]))
    for i, k in enumerate(knots):
        nc.Knots[i] = k
    return nc


def _json_to_nurbssurface(data):
    dim = data["dimension"]
    is_rat = data["is_rational"]
    order_u = data["order_u"]
    order_v = data["order_v"]
    n_u = data["cv_count_u"]
    n_v = data["cv_count_v"]
    rsrf = Rhino.Geometry.NurbsSurface.Create(dim, is_rat, order_u, order_v, n_u, n_v)
    for i, k in enumerate(data["knots_u"]):
        rsrf.KnotsU[i] = k
    for i, k in enumerate(data["knots_v"]):
        rsrf.KnotsV[i] = k
    cps = data["control_points"]
    stride = (dim + 1) if is_rat else dim
    for i in range(n_u):
        for j in range(n_v):
            idx = (i * n_v + j) * stride
            if is_rat:
                rsrf.Points.SetPoint(i, j, Rhino.Geometry.Point4d(cps[idx], cps[idx + 1], cps[idx + 2], cps[idx + 3]))
            else:
                rsrf.Points.SetPoint(i, j, Rhino.Geometry.Point3d(cps[idx], cps[idx + 1], cps[idx + 2]))
    return rsrf


def _eval_uv_loop_on_surface(rsrf, loop_data, n_samples=100):
    cps = loop_data["control_points"]
    loop_crv = _json_to_nurbscurve(loop_data)
    if loop_crv is None:
        return None
    dom = loop_crv.Domain
    pts = []
    for k in range(n_samples + 1):
        t = dom.T0 + (dom.T1 - dom.T0) * k / n_samples
        uv = loop_crv.PointAt(t)
        pt3d = rsrf.PointAt(uv.X, uv.Y)
        pts.append(pt3d)
    return Rhino.Geometry.Curve.CreateInterpolatedCurve(
        pts, 3, Rhino.Geometry.CurveKnotStyle.Chord)


def _add_nurbssurface(doc, data, colors):
    rsrf = _json_to_nurbssurface(data)
    name = data.get("name", "")
    has_outer = "outer_loop" in data and data["outer_loop"]
    g = System.Guid.Empty
    if has_outer:
        tol = doc.ModelAbsoluteTolerance
        curves_3d = [_eval_uv_loop_on_surface(rsrf, data["outer_loop"])]
        for il in data.get("inner_loops", []):
            c = _eval_uv_loop_on_surface(rsrf, il)
            if c:
                curves_3d.append(c)
        curves_3d = [c for c in curves_3d if c is not None]
        breps = Rhino.Geometry.Brep.CreatePlanarBreps(curves_3d, tol)
        if breps and len(breps) > 0:
            g = doc.Objects.AddBrep(breps[0])
        else:
            g = doc.Objects.AddSurface(rsrf)
    else:
        g = doc.Objects.AddSurface(rsrf)
    c = data.get("surfacecolor")
    if name in colors:
        _set_color(doc, g, *colors[name])
    elif c and (c.get("r") or c.get("g") or c.get("b")):
        _set_color(doc, g, c["r"], c["g"], c["b"])
    return g


def add_session(filepath, colors=None):
    doc = Rhino.RhinoDoc.ActiveDoc
    with open(filepath, "r") as f:
        data = json.load(f)
    objects = data.get("objects", {})
    if colors is None:
        colors = {}
    guids = []

    for srf_data in objects.get("nurbssurfaces", []):
        g = _add_nurbssurface(doc, srf_data, colors)
        if g != System.Guid.Empty:
            guids.append(g)
        if srf_data.get("mesh"):
            rmesh = _json_to_mesh(srf_data["mesh"])
            g = doc.Objects.AddMesh(rmesh)
            name = srf_data.get("name", "")
            if name in colors:
                _set_color(doc, g, *colors[name])
            guids.append(g)

    for mesh_data in objects.get("meshes", []):
        rmesh = _json_to_mesh(mesh_data)
        g = doc.Objects.AddMesh(rmesh)
        name = mesh_data.get("name", "")
        if name in colors:
            _set_color(doc, g, *colors[name])
        guids.append(g)

    for crv_data in objects.get("nurbscurves", []):
        rc = _json_to_nurbscurve(crv_data)
        if rc:
            g = doc.Objects.AddCurve(rc)
            name = crv_data.get("name", "")
            c = crv_data.get("linecolor")
            if name in colors:
                _set_color(doc, g, *colors[name])
            elif c and (c.get("r") or c.get("g") or c.get("b")):
                _set_color(doc, g, c["r"], c["g"], c["b"])
            guids.append(g)

    for pt_data in objects.get("points", []):
        g = doc.Objects.AddPoint(Rhino.Geometry.Point3d(pt_data["x"], pt_data["y"], pt_data["z"]))
        guids.append(g)

    doc.Views.Redraw()
    return guids


if __name__ == "__main__":
    add_session(
        r"c:\pc\3_code\code_rust\session\session_data\nurbs_meshing.json",
        colors={
            "freeform": (180, 100, 100),
            "freeform_mesh": (200, 120, 120),
            "planar": (100, 180, 100),
            "planar_mesh": (120, 200, 120),
            "rotated": (100, 100, 180),
            "rotated_mesh": (120, 120, 200),
            "holed": (180, 180, 100),
            "holed_mesh": (200, 200, 120),
        },
    )
