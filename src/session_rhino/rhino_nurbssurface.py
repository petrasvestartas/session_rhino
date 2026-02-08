import Rhino
import System


def _build_rhino_surface(srf):
    dim = srf.dimension()
    is_rat = srf.is_rational()
    order_u = srf.order(0)
    order_v = srf.order(1)
    n_u = srf.cv_count(0)
    n_v = srf.cv_count(1)
    rsrf = Rhino.Geometry.NurbsSurface.Create(dim, is_rat, order_u, order_v, n_u, n_v)
    knots_u = srf.get_knots(0)
    knots_v = srf.get_knots(1)
    for i, k in enumerate(knots_u):
        rsrf.KnotsU[i] = k
    for i, k in enumerate(knots_v):
        rsrf.KnotsV[i] = k
    for i in range(n_u):
        for j in range(n_v):
            if is_rat:
                ok, x, y, z, w = srf.get_cv_4d(i, j)
                rsrf.Points.SetPoint(i, j, Rhino.Geometry.Point4d(x, y, z, w))
            else:
                cv = srf.get_cv(i, j)
                rsrf.Points.SetPoint(i, j, Rhino.Geometry.Point3d(cv[0], cv[1], cv[2]))
    return rsrf


def _eval_loop_3d(srf, loop, rsrf):
    deg = loop.degree()
    pts = []
    for i in range(loop.cv_count()):
        uv = loop.get_cv(i)
        pt3d = rsrf.PointAt(uv[0], uv[1])
        pts.append(pt3d)
    if deg <= 1:
        pts.append(pts[0])
        return Rhino.Geometry.PolylineCurve([Rhino.Geometry.Point3d(p.X, p.Y, p.Z) for p in pts])
    return Rhino.Geometry.Curve.CreateInterpolatedCurve(
        pts, deg, Rhino.Geometry.CurveKnotStyle.Chord)


def to_rhino(srf):
    rsrf = _build_rhino_surface(srf)
    if not srf.is_trimmed():
        return rsrf
    tol = Rhino.RhinoDoc.ActiveDoc.ModelAbsoluteTolerance
    outer_loop = srf.get_outer_loop()
    curves_3d = [_eval_loop_3d(srf, outer_loop, rsrf)]
    for i in range(srf.inner_loop_count()):
        curves_3d.append(_eval_loop_3d(srf, srf.get_inner_loop(i), rsrf))
    breps = Rhino.Geometry.Brep.CreatePlanarBreps(curves_3d, tol)
    if breps and len(breps) > 0:
        return breps[0]
    brep = rsrf.ToBrep()
    if brep and brep.Faces.Count > 0:
        split_breps = brep.Faces[0].Split(curves_3d, tol)
        if split_breps:
            return split_breps
    return rsrf


def add(obj_or_list, **kwargs):
    if not isinstance(obj_or_list, list):
        obj_or_list = [obj_or_list]
    guids = []
    doc = Rhino.RhinoDoc.ActiveDoc
    for srf in obj_or_list:
        robj = to_rhino(srf)
        if isinstance(robj, Rhino.Geometry.Brep):
            guid = doc.Objects.AddBrep(robj)
        elif isinstance(robj, Rhino.Geometry.NurbsSurface):
            guid = doc.Objects.AddSurface(robj)
        else:
            guid = doc.Objects.AddBrep(robj)
        obj = doc.Objects.Find(guid)
        if obj is not None and srf.surfacecolor is not None:
            attr = obj.Attributes
            attr.ObjectColor = System.Drawing.Color.FromArgb(
                srf.surfacecolor.r, srf.surfacecolor.g, srf.surfacecolor.b)
            attr.ColorSource = Rhino.DocObjects.ObjectColorSource.ColorFromObject
            doc.Objects.ModifyAttributes(guid, attr, True)
        guids.append(guid)
    doc.Views.Redraw()
    return guids
