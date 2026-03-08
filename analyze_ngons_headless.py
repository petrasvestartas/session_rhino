import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
sys.path.insert(0, r'C:\pc\3_code\code_rust\session\session_py\src')

import rhinoinside
rhinoinside.load(r"C:\Program Files\Rhino 8\System")
import Rhino  # noqa: E402

from session_py.session import Session
from session_rhino import rhino_mesh as rm

PB = r'C:\pc\3_code\code_rust\session\session_data\mesh_quad_tri_loft12_out.pb'

doc = Rhino.RhinoDoc.CreateHeadless(None)
Rhino.RhinoDoc.ActiveDoc = doc
data = Session.pb_load(PB)

for mi, mesh in enumerate(data.objects.meshes):
    rmesh = rm.to_rhino(mesh)
    valid, log = rmesh.IsValidWithLog()
    print(f"\nmesh[{mi}] '{mesh.name}': IsValid={valid}  NGons={rmesh.Ngons.Count}")
    if not valid:
        print(f"  log: {log[:400]}")

    nv = rmesh.Vertices.Count
    nf = rmesh.Faces.Count
    for ni in range(rmesh.Ngons.Count):
        ngon = rmesh.Ngons.GetNgon(ni)
        if ngon is None:
            print(f"  NGon[{ni}]: None!")
            continue
        bv = list(ngon.BoundaryVertexIndexList())
        fi_list = list(ngon.FaceIndexList())
        oob_v = [v for v in bv if v < 0 or v >= nv]
        oob_f = [f for f in fi_list if f < 0 or f >= nf]
        if oob_v or oob_f:
            print(f"  NGon[{ni}]: OOB verts={oob_v} faces={oob_f}")

doc.Dispose()
