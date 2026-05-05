import Rhino
import System


def from_rhino(rpl):
    from session_py import Polyline as SPPolyline
    from session_py.brep import _IDENTITY_XFORM, _ZERO_GUID
    from session_py.plane import Plane
    vertices = rpl.ToPolyline() if hasattr(rpl, 'ToPolyline') else rpl
    pl = SPPolyline.__new__(SPPolyline)
    pl.guid = _ZERO_GUID; pl.name = ""; pl.width = 1.0
    pl.linecolor = None; pl.xform = _IDENTITY_XFORM; pl.plane = Plane()
    pl.coords = []
    for v in vertices:
        pl.coords.extend([float(v.X), float(v.Y), float(v.Z)])
    return pl


def to_rhino(pl):
    coords = pl.coords
    rpl = Rhino.Geometry.Polyline()
    prev = None
    for i in range(pl.point_count()):
        j = i * 3
        pt = Rhino.Geometry.Point3d(coords[j], coords[j + 1], coords[j + 2])
        if prev is None or pt.DistanceTo(prev) > 1e-10:
            rpl.Add(pt)
            prev = pt
    if rpl.Count < 2:
        return None
    return Rhino.Geometry.PolylineCurve(rpl)


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
