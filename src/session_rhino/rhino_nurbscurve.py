import Rhino
import System


def to_rhino(crv):
    dim = 3
    is_rat = crv.is_rational()
    order = crv.order()
    cv_count = crv.cv_count()
    nc = Rhino.Geometry.NurbsCurve(dim, is_rat, order, cv_count)
    for i in range(crv.knot_count()):
        nc.Knots[i] = float(crv.knot(i))
    if is_rat:
        for i in range(cv_count):
            x, y, z, w = crv.get_cv_4d(i)
            nc.Points.SetPoint(i, Rhino.Geometry.Point4d(float(x), float(y), float(z), float(w)))
    else:
        for i in range(cv_count):
            cv = crv.get_cv(i)
            nc.Points.SetPoint(i, Rhino.Geometry.Point3d(float(cv.x), float(cv.y), float(cv.z)))
    return nc


def _apply_attributes(doc, guid, crv):
    obj = doc.Objects.Find(guid)
    if obj is None:
        return
    attr = obj.Attributes
    changed = False
    color = None
    if len(crv.linecolors) > 0:
        color = crv.linecolors[0]
    elif len(crv.pointcolors) > 0:
        color = crv.pointcolors[0]
    if color is not None:
        attr.ObjectColor = System.Drawing.Color.FromArgb(color[3], color[0], color[1], color[2])
        attr.ColorSource = Rhino.DocObjects.ObjectColorSource.ColorFromObject
        changed = True
    if crv.width > 0 and crv.width != 1.0:
        attr.PlotWeight = crv.width
        attr.PlotWeightSource = Rhino.DocObjects.ObjectPlotWeightSource.PlotWeightFromObject
        changed = True
    if changed:
        doc.Objects.ModifyAttributes(guid, attr, True)


def add(obj_or_list, **kwargs):
    if not isinstance(obj_or_list, list):
        obj_or_list = [obj_or_list]
    guids = []
    doc = Rhino.RhinoDoc.ActiveDoc
    for crv in obj_or_list:
        rcrv = to_rhino(crv)
        if rcrv is None or not rcrv.IsValid:
            continue
        guid = doc.Objects.AddCurve(rcrv)
        if guid == System.Guid.Empty:
            continue
        _apply_attributes(doc, guid, crv)
        guids.append(guid)
    doc.Views.Redraw()
    return guids
