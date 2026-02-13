import Rhino
import System


def to_rhino(ln):
    return Rhino.Geometry.Line(
        Rhino.Geometry.Point3d(ln[0], ln[1], ln[2]),
        Rhino.Geometry.Point3d(ln[3], ln[4], ln[5])
    )


def _apply_attributes(doc, guid, ln):
    obj = doc.Objects.Find(guid)
    if obj is None:
        return
    attr = obj.Attributes
    changed = False
    if ln.linecolor is not None:
        attr.ObjectColor = System.Drawing.Color.FromArgb(ln.linecolor.a, ln.linecolor.r, ln.linecolor.g, ln.linecolor.b)
        attr.ColorSource = Rhino.DocObjects.ObjectColorSource.ColorFromObject
        changed = True
    if ln.width > 0 and ln.width != 1.0:
        attr.PlotWeight = ln.width
        attr.PlotWeightSource = Rhino.DocObjects.ObjectPlotWeightSource.PlotWeightFromObject
        changed = True
    if changed:
        doc.Objects.ModifyAttributes(guid, attr, True)


def add(obj_or_list, **kwargs):
    if not isinstance(obj_or_list, list):
        obj_or_list = [obj_or_list]
    guids = []
    doc = Rhino.RhinoDoc.ActiveDoc
    for ln in obj_or_list:
        rln = to_rhino(ln)
        guid = doc.Objects.AddLine(rln)
        if guid != System.Guid.Empty:
            _apply_attributes(doc, guid, ln)
        guids.append(guid)
    doc.Views.Redraw()
    return guids
