#! python3
# venv: session_py

from session_py.reload import reload_all
import session_rhino
reload_all()

from session_rhino.session import Session

filepath = r"c:\pc\3_code\code_rust\session\session_data\create_network2.pb"
data = Session.load(filepath)

scene = Session()

for crv in data.objects.nurbscurves:
    scene.add(crv)

for srf in data.objects.nurbssurfaces:
    scene.add(srf)
    scene.add(srf.mesh())

# print(data.objects.meshes)
# for mesh in data.objects.meshes:
#     scene.add(mesh)

print("scene items:", len(scene._scene))
guids = scene.draw(delete=True)
print("guids:", guids)
