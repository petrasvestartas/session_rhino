#! python3
# venv: session_py

from session_py.reload import reload_all
import session_rhino
reload_all()

from session_rhino.session import Session
from session_py.session import Session as PySession
from session_rhino.rhino_mesh import to_rhino
import Rhino
import System

filepath = r"c:\pc\3_code\code_rust\session\session_data\mesh_quad_tri_loft7_out.pb"

data = PySession.pb_load(filepath)
meshes = list(data.objects.meshes)

scene = Session.load(filepath)
scene.draw(delete=True)

doc = Rhino.RhinoDoc.ActiveDoc

FAIL_IDX = [0, 25, 108]
for i in FAIL_IDX:
    obj = meshes[i]
    rmesh = to_rhino(obj)
    ok, log = rmesh.IsValidWithLog()
    print(f"\nmesh[{i}] verts={rmesh.Vertices.Count} faces={rmesh.Faces.Count} ngons={rmesh.Ngons.Count} valid={ok}")
    if not ok:
        print(f"  log: {log.strip()}")
    face_sizes = sorted(set(len(f) for f in obj.face.values()))
    print(f"  python face_sizes={face_sizes}")
    for fk, fverts in list(obj.face.items())[:5]:
        tri = obj.triangulation.get(fk)
        print(f"  face {fk}: n={len(fverts)} tri={tri}")

doc.Views.Redraw()
