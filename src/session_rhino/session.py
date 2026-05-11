import json
import scriptcontext as sc

import Rhino
import System

from session_py.mesh import Mesh
from session_py.polyline import Polyline
from session_rhino.rhino_mesh import add as _add_mesh
from session_rhino.rhino_mesh import add_joined as _add_mesh_joined
from session_rhino.rhino_polyline import add as _add_polyline

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


class Session:
    """Rhino scene manager — queue objects with add(), display with draw().

    draw() deletes objects from the previous call, adds all queued objects
    to the document, tracks their GUIDs, and redraws the viewport.
    This makes it safe to call draw() repeatedly (e.g. inside a
    process_input callback) without leaving orphaned geometry.

    Usage::

        session = Session()

        def _run(v, _):
            shell, elements = translation_shell_elements(...)
            session.add(shell)
            for el in elements:
                session.add(el.bottom, el.top, el.loft_mesh())
            session.draw()
    """

    def __init__(self):
        self._scene = []   # queued (obj, kwargs) pairs
        self._joined = []  # queued (meshes, kwargs) pairs for joined adds
        self._guids = []   # GUIDs added by the last draw()

    @staticmethod
    def load(filepath):
        """Load a session_py Session from a .pb or .json file."""
        import importlib
        from session_py.session import Session as PySession

        if str(filepath).endswith(".pb"):
            data = PySession.pb_load(filepath)
        else:
            with open(filepath, "r") as f:
                import json as _json
                raw = _json.load(f)
            data = PySession.__jsonload__(raw)

        session = Session()
        for col in [
            data.objects.points, data.objects.lines, data.objects.planes,
            data.objects.polylines, data.objects.meshes,
            data.objects.nurbscurves, data.objects.nurbssurfaces, data.objects.breps,
        ]:
            for obj in col:
                session._scene.append((obj, {}))
        return session

    def add(self, *objects, **kwargs):
        """Queue session_py objects for the next draw() call."""
        for obj in objects:
            self._scene.append((obj, kwargs))

    def add_joined(self, *meshes, **kwargs):
        """Queue a list of Meshes to be joined into a single Rhino object on draw().

        Use instead of looping session.add() for large collections of plate/loft
        meshes — reduces N doc.Objects.AddMesh() calls to 1, which avoids the
        repeated document-event overhead that makes bulk display slow.
        """
        from session_py.mesh import Mesh
        self._joined.append(([m for m in meshes if isinstance(m, Mesh)], kwargs))

    def draw(self):
        """Delete previous objects, add queued objects, redraw."""
        doc = Rhino.RhinoDoc.ActiveDoc

        for g in self._guids:
            doc.Objects.Delete(g, True)
        self._guids.clear()

        doc.Views.EnableRedraw(False, False, False)
        try:
            for obj, _ in self._scene:
                if isinstance(obj, Mesh):
                    self._guids.extend(_add_mesh(obj))
                elif isinstance(obj, Polyline):
                    self._guids.extend(_add_polyline(obj))
                else:
                    type_name = type(obj).__name__
                    if type_name in _MODULE_MAP:
                        import importlib
                        mod = importlib.import_module(_MODULE_MAP[type_name])
                        rhino_geo = mod.to_rhino(obj)
                        if rhino_geo is None:
                            continue
                        if isinstance(rhino_geo, Rhino.Geometry.Mesh):
                            g = doc.Objects.AddMesh(rhino_geo)
                        elif isinstance(rhino_geo, Rhino.Geometry.Curve):
                            g = doc.Objects.AddCurve(rhino_geo)
                        elif isinstance(rhino_geo, Rhino.Geometry.Point3d):
                            g = doc.Objects.AddPoint(rhino_geo)
                        elif isinstance(rhino_geo, Rhino.Geometry.Brep):
                            g = doc.Objects.AddBrep(rhino_geo)
                        elif isinstance(rhino_geo, Rhino.Geometry.Surface):
                            g = doc.Objects.AddSurface(rhino_geo)
                        else:
                            continue
                        if g != System.Guid.Empty:
                            self._guids.append(g)

            for meshes, _ in self._joined:
                self._guids.extend(_add_mesh_joined(meshes))
        finally:
            doc.Views.EnableRedraw(True, False, False)

        self._scene.clear()
        self._joined.clear()
        sc.doc.Views.Redraw()
