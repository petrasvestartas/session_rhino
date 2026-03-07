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
        if delete:
            for guid_str in _load_guids():
                doc.Objects.Delete(System.Guid(guid_str), True)

        guid_map = {}
        new_guids = []
        for obj, kwargs in self._scene:
            type_name = type(obj).__name__
            if type_name not in _MODULE_MAP:
                continue
            module = _get_module(type_name)
            rhino_guids = module.add(obj, **kwargs)
            if hasattr(obj, "guid"):
                guid_map[obj.guid] = rhino_guids
            new_guids.extend(str(g) for g in rhino_guids)

        if self._tree and self._tree.root:
            layer_map = {}
            for node in self._tree.root.children:
                if node.name not in self._lookup:
                    layer_idx = doc.Layers.FindByFullPath(node.name, -1)
                    if layer_idx < 0:
                        layer_obj = Rhino.DocObjects.Layer()
                        layer_obj.Name = node.name
                        if node.color is not None:
                            layer_obj.Color = System.Drawing.Color.FromArgb(
                                node.color[3], node.color[0], node.color[1], node.color[2])
                        layer_idx = doc.Layers.Add(layer_obj)
                    layer_map[node.name] = layer_idx
            for node in self._tree.root.children:
                if node.name not in layer_map:
                    continue
                layer_idx = layer_map[node.name]
                for desc in node.traverse():
                    for rhino_guid in guid_map.get(desc.name, []):
                        obj = doc.Objects.Find(rhino_guid)
                        if obj is None:
                            continue
                        attr = obj.Attributes
                        attr.LayerIndex = layer_idx
                        doc.Objects.ModifyAttributes(rhino_guid, attr, True)
            for node in self._tree.nodes:
                if not node.children or node.name not in self._lookup:
                    continue
                group_guids = list(guid_map.get(node.name, []))
                for child in node.children:
                    group_guids.extend(guid_map.get(child.name, []))
                valid = [g for g in group_guids if g != System.Guid.Empty]
                if len(valid) < 2:
                    continue
                doc.Groups.Add(valid)

        self._scene.clear()
        if delete:
            _save_guids(new_guids)
        else:
            _save_guids(_load_guids() + new_guids)
        doc.Views.Redraw()
        return new_guids

    def to_rhino(self, obj):
        module = _get_module(type(obj).__name__)
        return module.to_rhino(obj)
