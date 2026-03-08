import Rhino
import System


def to_rhino(ln):
    return Rhino.Geometry.Line(
        Rhino.Geometry.Point3d(ln[0], ln[1], ln[2]),
        Rhino.Geometry.Point3d(ln[3], ln[4], ln[5])
    )


def add(obj_or_list, layer_idx=0, **kwargs):
    if not isinstance(obj_or_list, list):
        obj_or_list = [obj_or_list]
    guids = []
    doc = Rhino.RhinoDoc.ActiveDoc
    for ln in obj_or_list:
        rln = to_rhino(ln)
        attr = Rhino.DocObjects.ObjectAttributes()
        attr.LayerIndex = layer_idx
        if ln.linecolor is not None:
            attr.ObjectColor = System.Drawing.Color.FromArgb(ln.linecolor.a, ln.linecolor.r, ln.linecolor.g, ln.linecolor.b)
            attr.ColorSource = Rhino.DocObjects.ObjectColorSource.ColorFromObject
        if ln.width > 0 and ln.width != 1.0:
            attr.PlotWeight = ln.width
            attr.PlotWeightSource = Rhino.DocObjects.ObjectPlotWeightSource.PlotWeightFromObject
        guids.append(doc.Objects.AddLine(rln, attr))
    return guids
