#! python3
# venv: session_py

from session_py.reload import reload_all
import session_rhino
reload_all()

from session_rhino.session import Session

filepath = r"c:\pc\3_code\code_rust\session\session_data\nurbs_meshing_3.json"
data = Session.load(filepath)
print(data.objects.nurbssurfaces)

scene = Session()

for srf in data.objects.nurbssurfaces:
    mesh = srf.mesh()
    print("mesh:", mesh.number_of_vertices(), mesh.number_of_faces())
    scene.add(srf)
    if mesh is not None:
        scene.add(mesh)

for line in data.objects.lines:
    scene.add(line)

print("scene items:", len(scene._scene))
guids = scene.draw(delete=True)
print("guids:", guids)
