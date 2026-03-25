#! python3
# venv: session_py
from session_py.session import Session as PySession
from session_rhino.rhino_mesh import to_rhino

filepath = r"C:\pc\3_code\code_rust\session\session_data\RemeshNurbsSurfaceGrid.pb"

data = PySession.pb_load(filepath)
meshes = list(data.objects.meshes)
print(f"meshes in pb: {len(meshes)}")

for mesh in meshes:
    print(f"  [{mesh.name}] verts={mesh.number_of_vertices()} faces={mesh.number_of_faces()} valid={mesh.is_valid()}")
    rmesh = to_rhino(mesh)
    valid, log = rmesh.IsValidWithLog()
    print(f"    rhino: verts={rmesh.Vertices.Count} faces={rmesh.Faces.Count} valid={valid}")
    if not valid:
        print(f"    reason: {log.strip()}")
