import Rhino
import System


def to_rhino(pt):
    return Rhino.Geometry.Point3d(pt.x, pt.y, pt.z)


def add(obj_or_list, layer_idx=0, **kwargs):
    if not isinstance(obj_or_list, list):
        obj_or_list = [obj_or_list]
    guids = []
    doc = Rhino.RhinoDoc.ActiveDoc
    for pt in obj_or_list:
        rpt = to_rhino(pt)
        attr = Rhino.DocObjects.ObjectAttributes()
        attr.LayerIndex = layer_idx
        if pt.pointcolor is not None:
            attr.ObjectColor = System.Drawing.Color.FromArgb(pt.pointcolor.r, pt.pointcolor.g, pt.pointcolor.b)
            attr.ColorSource = Rhino.DocObjects.ObjectColorSource.ColorFromObject
        if pt.name and pt.name != "my_point":
            guid = doc.Objects.AddTextDot(pt.name, rpt)
            if guid != System.Guid.Empty:
                obj = doc.Objects.FindId(guid)
                if obj:
                    obj.Attributes.LayerIndex = layer_idx
                    obj.CommitChanges()
            guids.append(guid)
        else:
            guids.append(doc.Objects.AddPoint(rpt, attr))
    return guids
