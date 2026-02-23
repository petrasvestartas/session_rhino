#! python3
# venv: session_py

from session_py.reload import reload_all
import session_rhino
reload_all()

from session_rhino.session import Session

filepath = r"c:\pc\3_code\code_rust\session\session_data\brep_demo.pb"
data = Session.load(filepath)

scene = Session()

for crv in data.objects.nurbscurves:
    scene.add(crv)

for srf in data.objects.nurbssurfaces:
    scene.add(srf)

for mesh in data.objects.meshes:
    scene.add(mesh)

for ln in data.objects.lines:
    scene.add(ln)

for pt in data.objects.points:
    scene.add(pt)

for pl in data.objects.polylines:
    scene.add(pl)

for brep in data.objects.breps:
    scene.add(brep)

guids = scene.draw(delete=True)
print("guids:", guids)