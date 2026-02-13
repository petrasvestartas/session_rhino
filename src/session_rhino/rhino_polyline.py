import Rhino
import System


def to_rhino(pl):
    pts = []
    for p in pl.get_points():
        pts.append(Rhino.Geometry.Point3d(float(p[0]), float(p[1]), float(p[2])))
    return Rhino.Geometry.PolylineCurve(pts)


def _apply_attributes(doc, guid, pl):
    obj = doc.Objects.Find(guid)
    if obj is None:
        return
    attr = obj.Attributes
    changed = False
    if pl.linecolor is not None:
        attr.ObjectColor = System.Drawing.Color.FromArgb(pl.linecolor.a, pl.linecolor.r, pl.linecolor.g, pl.linecolor.b)
        attr.ColorSource = Rhino.DocObjects.ObjectColorSource.ColorFromObject
        changed = True
    if pl.width > 0 and pl.width != 1.0:
        attr.PlotWeight = pl.width
        attr.PlotWeightSource = Rhino.DocObjects.ObjectPlotWeightSource.PlotWeightFromObject
        changed = True
    if changed:
        doc.Objects.ModifyAttributes(guid, attr, True)


def add(obj_or_list, **kwargs):
    if not isinstance(obj_or_list, list):
        obj_or_list = [obj_or_list]
    guids = []
    doc = Rhino.RhinoDoc.ActiveDoc
    for pl in obj_or_list:
        rpl = to_rhino(pl)
        if rpl is None or not rpl.IsValid:
            continue
        guid = doc.Objects.AddCurve(rpl)
        if guid == System.Guid.Empty:
            continue
        _apply_attributes(doc, guid, pl)
        guids.append(guid)
    doc.Views.Redraw()
    return guids
