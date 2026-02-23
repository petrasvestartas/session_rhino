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


def to_rhino(srf):
    return _build_rhino_surface(srf)


def _apply_attributes(doc, guid, srf):
    obj = doc.Objects.Find(guid)
    if obj is None:
        return
    attr = obj.Attributes
    changed = False
    color = None
    if len(srf.facecolors) > 0:
        color = srf.facecolors[0]
    elif len(srf.linecolors) > 0:
        color = srf.linecolors[0]
    elif len(srf.pointcolors) > 0:
        color = srf.pointcolors[0]
    if color is not None:
        attr.ObjectColor = System.Drawing.Color.FromArgb(color[3], color[0], color[1], color[2])
        attr.ColorSource = Rhino.DocObjects.ObjectColorSource.ColorFromObject
        changed = True
    if changed:
        doc.Objects.ModifyAttributes(guid, attr, True)


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
        _apply_attributes(doc, guid, srf)
        guids.append(guid)
    doc.Views.Redraw()
    return guids
