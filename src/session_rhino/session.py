import Rhino
import importlib
import System
import json
import tempfile
from pathlib import Path

_GUID_FILE = Path(tempfile.gettempdir()) / "session_rhino_guids.json"

_MODULE_MAP = {
    "Point":        "session_rhino.rhino_point",
    "Line":         "session_rhino.rhino_line",
    "Plane":        "session_rhino.rhino_plane",
    "Mesh":         "session_rhino.rhino_mesh",
    "NurbsCurve":   "session_rhino.rhino_nurbscurve",
    "Polyline":     "session_rhino.rhino_polyline",
    "NurbsSurface": "session_rhino.rhino_nurbssurface",
    "BRep":         "session_rhino.rhino_brep",
}


def _get_module(type_name):
    return importlib.import_module(_MODULE_MAP[type_name])


def _load_guids():
    if _GUID_FILE.exists():
        return json.loads(_GUID_FILE.read_text())
    return []


def _save_guids(guids):
    _GUID_FILE.write_text(json.dumps(guids))


class Session:
    def __init__(self):
        self._scene = []
        self._tree = None
        self._lookup = None

    @staticmethod
    def load(filepath):
        from session_py.session import Session as PySession

        if str(filepath).endswith(".pb"):
            data = PySession.pb_load(filepath)
        else:
            with open(filepath, "r") as f:
                raw = json.load(f)
            data = PySession.__jsonload__(raw)

        session = Session()
        collections = [
            data.objects.points, data.objects.lines, data.objects.planes,
            data.objects.polylines, data.objects.meshes,
            data.objects.nurbscurves, data.objects.nurbssurfaces, data.objects.breps,
        ]
        for col in collections:
            for obj in col:
                session._scene.append((obj, {}))
        session._tree = data.tree
        session._lookup = data.lookup
        return session

    def add(self, obj_or_list, **kwargs):
        if not isinstance(obj_or_list, list):
            obj_or_list = [obj_or_list]
        for obj in obj_or_list:
            self._scene.append((obj, kwargs))

    def draw(self, delete=True):
        doc = Rhino.RhinoDoc.ActiveDoc
        old_guids = _load_guids() if delete else []

        # Build layer mapping from tree
        guid_to_layer = {}
        layer_names = {}
        if self._tree and self._tree.root:
            for node in self._tree.root.children:
                if node.name not in self._lookup:
                    layer_names[node.name] = node.color
            for node in self._tree.root.children:
                if node.name not in layer_names:
                    continue
                for desc in node.traverse():
                    guid_to_layer[desc.name] = node.name

        # Build File3dm with all geometry
        f3dm = Rhino.FileIO.File3dm()

        # Create layers in File3dm
        f3dm_layer_map = {}
        for lname, lcolor in layer_names.items():
            layer = Rhino.DocObjects.Layer()
            layer.Name = lname
            if lcolor is not None:
                layer.Color = System.Drawing.Color.FromArgb(lcolor[3], lcolor[0], lcolor[1], lcolor[2])
            f3dm.AllLayers.Add(layer)
            f3dm_layer_map[lname] = f3dm.AllLayers.Count - 1

        # Collect planes and per-element grouped objects — drawn separately
        # into active doc after import so we can create Rhino groups.
        plane_objs = []
        # group_key -> [(obj, layer_name)] for objects that need Rhino grouping
        grouped_objs = {}

        # Convert all objects and add to File3dm
        _module_cache = {}
        for obj, kwargs in self._scene:
            type_name = type(obj).__name__
            if type_name not in _MODULE_MAP:
                continue

            if type_name == "Plane":
                plane_objs.append(obj)
                continue

            # Check if this object belongs to a per-element group (element_N)
            # If so, draw it directly to the doc later with Rhino grouping.
            obj_guid = getattr(obj, 'guid', None)
            layer_name = guid_to_layer.get(obj_guid)
            if layer_name and layer_name.startswith("element_"):
                grouped_objs.setdefault(layer_name, []).append((obj, layer_name))
                continue

            if type_name not in _module_cache:
                _module_cache[type_name] = _get_module(type_name)
            module = _module_cache[type_name]
            rhino_geo = module.to_rhino(obj)
            if rhino_geo is None:
                continue
            attr = Rhino.DocObjects.ObjectAttributes()
            if layer_name and layer_name in f3dm_layer_map:
                attr.LayerIndex = f3dm_layer_map[layer_name]
            attr.Name = getattr(obj, 'name', '')
            # Set color
            color = None
            if type_name == "Mesh":
                from session_py.mesh import ColorMode
                mode = obj.color_mode
                if mode == ColorMode.OBJECTCOLOR:
                    oc = obj.objectcolor
                    if oc[0] != 255 or oc[1] != 255 or oc[2] != 255:
                        color = oc
            elif isinstance(obj, object) and hasattr(obj, 'linecolor') and obj.linecolor is not None:
                lc = obj.linecolor
                if lc[0] != 255 or lc[1] != 255 or lc[2] != 255:
                    color = lc
            if color is not None:
                attr.ObjectColor = System.Drawing.Color.FromArgb(color[3], color[0], color[1], color[2])
                attr.ColorSource = Rhino.DocObjects.ObjectColorSource.ColorFromObject
            # Add to File3dm by type
            if isinstance(rhino_geo, Rhino.Geometry.Mesh):
                f3dm.Objects.AddMesh(rhino_geo, attr)
            elif isinstance(rhino_geo, Rhino.Geometry.Curve):
                f3dm.Objects.AddCurve(rhino_geo, attr)
            elif isinstance(rhino_geo, Rhino.Geometry.Point3d):
                f3dm.Objects.AddPoint(rhino_geo)
            elif isinstance(rhino_geo, Rhino.Geometry.Brep):
                f3dm.Objects.AddBrep(rhino_geo, attr)
            elif isinstance(rhino_geo, Rhino.Geometry.Surface):
                f3dm.Objects.AddSurface(rhino_geo, attr)

        # Write to temp file and import
        import tempfile, os
        tmp = tempfile.mktemp(suffix=".3dm")
        f3dm.Write(tmp, 8)

        doc.Views.RedrawEnabled = False
        doc.Views.EnableRedraw(False, False, False)
        try:
            for guid_str in old_guids:
                doc.Objects.Delete(System.Guid(guid_str), True)
            scriptcontext = __import__('scriptcontext')
            scriptcontext.doc.Import(tmp)

            # Draw planes directly to active doc with grouping
            if plane_objs:
                pl_module = _get_module("Polyline")
                for plane_obj in plane_objs:
                    obj_guid = getattr(plane_obj, 'guid', None)
                    layer_name = guid_to_layer.get(obj_guid)
                    layer_idx = 0
                    if layer_name:
                        found = doc.Layers.FindName(layer_name) if hasattr(doc.Layers, 'FindName') else None
                        if found:
                            layer_idx = found.Index
                    plane_guids = []
                    for pl in plane_obj.to_polylines(plane_obj.width):
                        rhino_geo = pl_module.to_rhino(pl)
                        if rhino_geo is None:
                            continue
                        attr = Rhino.DocObjects.ObjectAttributes()
                        attr.LayerIndex = layer_idx
                        attr.Name = getattr(plane_obj, 'name', '')
                        lc = pl.linecolor
                        if lc[0] != 255 or lc[1] != 255 or lc[2] != 255:
                            attr.ObjectColor = System.Drawing.Color.FromArgb(lc[3], lc[0], lc[1], lc[2])
                            attr.ColorSource = Rhino.DocObjects.ObjectColorSource.ColorFromObject
                        gid = doc.Objects.AddCurve(rhino_geo, attr)
                        if gid != System.Guid.Empty:
                            plane_guids.append(gid)
                    if plane_guids:
                        doc.Groups.Add(plane_guids)

            # Draw per-element grouped objects directly to doc with Rhino groups
            if grouped_objs:
                for group_name, obj_list in grouped_objs.items():
                    layer_idx = 0
                    found = doc.Layers.FindName(group_name) if hasattr(doc.Layers, 'FindName') else None
                    if not found:
                        li = Rhino.DocObjects.Layer()
                        li.Name = group_name
                        layer_idx = doc.Layers.Add(li)
                    else:
                        layer_idx = found.Index
                    element_guids = []
                    for obj, _ in obj_list:
                        type_name = type(obj).__name__
                        if type_name not in _module_cache:
                            _module_cache[type_name] = _get_module(type_name)
                        module = _module_cache[type_name]
                        rhino_geo = module.to_rhino(obj)
                        if rhino_geo is None:
                            continue
                        attr = Rhino.DocObjects.ObjectAttributes()
                        attr.LayerIndex = layer_idx
                        attr.Name = getattr(obj, 'name', '')
                        lc = getattr(obj, 'linecolor', None)
                        if lc is not None and (lc[0] != 255 or lc[1] != 255 or lc[2] != 255):
                            attr.ObjectColor = System.Drawing.Color.FromArgb(lc[3], lc[0], lc[1], lc[2])
                            attr.ColorSource = Rhino.DocObjects.ObjectColorSource.ColorFromObject
                        if isinstance(rhino_geo, Rhino.Geometry.Mesh):
                            gid = doc.Objects.AddMesh(rhino_geo, attr)
                        elif isinstance(rhino_geo, Rhino.Geometry.Curve):
                            gid = doc.Objects.AddCurve(rhino_geo, attr)
                        elif isinstance(rhino_geo, Rhino.Geometry.Point3d):
                            gid = doc.Objects.AddPoint(rhino_geo)
                        elif isinstance(rhino_geo, Rhino.Geometry.Brep):
                            gid = doc.Objects.AddBrep(rhino_geo, attr)
                        elif isinstance(rhino_geo, Rhino.Geometry.Surface):
                            gid = doc.Objects.AddSurface(rhino_geo, attr)
                        else:
                            continue
                        if gid != System.Guid.Empty:
                            element_guids.append(gid)
                    if element_guids:
                        doc.Groups.Add(group_name, element_guids)
        finally:
            doc.Views.EnableRedraw(True, False, False)
            doc.Views.RedrawEnabled = True

        try:
            os.remove(tmp)
        except:
            pass

        self._scene.clear()
        _save_guids([])
        doc.Views.Redraw()
        return []

    def to_rhino(self, obj):
        module = _get_module(type(obj).__name__)
        return module.to_rhino(obj)
