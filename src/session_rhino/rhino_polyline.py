import Rhino
import System


def to_rhino(pl):
    pts = []
    for p in pl.get_points():
        pts.append(Rhino.Geometry.Point3d(float(p[0]), float(p[1]), float(p[2])))
    return Rhino.Geometry.PolylineCurve(pts)


def add(obj_or_list, layer_idx=0, **kwargs):
    if not isinstance(obj_or_list, list):
        obj_or_list = [obj_or_list]
    guids = []
    doc = Rhino.RhinoDoc.ActiveDoc
    for pl in obj_or_list:
        rpl = to_rhino(pl)
        if rpl is None or not rpl.IsValid:
            continue
        attr = Rhino.DocObjects.ObjectAttributes()
        attr.LayerIndex = layer_idx
        if pl.linecolor is not None:
            attr.ObjectColor = System.Drawing.Color.FromArgb(pl.linecolor.a, pl.linecolor.r, pl.linecolor.g, pl.linecolor.b)
            attr.ColorSource = Rhino.DocObjects.ObjectColorSource.ColorFromObject
        if pl.width > 0 and pl.width != 1.0:
            attr.PlotWeight = pl.width
            attr.PlotWeightSource = Rhino.DocObjects.ObjectPlotWeightSource.PlotWeightFromObject
        guid = doc.Objects.AddCurve(rpl, attr)
        if guid == System.Guid.Empty:
            continue
        guids.append(guid)
    return guids
