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

filepath = r"C:\pc\3_code\code_rust\session\session_data\mesh_quad_tri_loft13_out.pb"
# filepath = r"c:\pc\3_code\code_rust\session\session_data\mesh_recheck.pb"

data = PySession.pb_load(filepath)
meshes = list(data.objects.meshes)

                                                                                                                                                                                                                                
import session_rhino.rhino_mesh as _rm
print(_rm.__file__)
mesh = meshes[0]
print(f"face_holes={len(mesh.face_holes)} triangulation={len(mesh.triangulation)}")
rmesh = to_rhino(mesh)
print(f"ngons={rmesh.Ngons.Count}")

scene = Session.load(filepath)
scene.draw(delete=True)
