#! python3                                                                                                     
# venv: session_py                                                                                                                                                                                                                        

from session_py.reload import reload_all
import session_rhino
reload_all()

from session_py.session import Session as PySession
import session_rhino.rhino_brep as _rb
import Rhino

filepath = r"C:\pc\3_code\code_rust\session\session_data\mesh_quad_tri_loft0_out.pb"
data = PySession.pb_load(filepath)
breps = list(data.objects.breps)
meshes = list(data.objects.meshes)
print(f"Loaded: {len(breps)} breps, {len(meshes)} meshes")

doc_tol = Rhino.RhinoDoc.ActiveDoc.ModelAbsoluteTolerance
print(f"doc_tol = {doc_tol}")

b = breps[0]
face = b.m_faces[0]
srf = b.m_surfaces[face.surface_index]

print("\n[Surface CVs (bounding-box corners)]:")
for vi in range(srf.cv_count(0)):
    for vj in range(srf.cv_count(1)):
        cv = srf.get_cv(vi, vj)
        print(f"  cv[{vi},{vj}] = ({cv[0]:.3f}, {cv[1]:.3f}, {cv[2]:.3f})")

outer_li = next((li for li in face.loop_indices if b.m_loops[li].type == 0), None)
loop = b.m_loops[outer_li]
for ti in loop.trim_indices:
    trim = b.m_trims[ti]
    edge = b.m_topology_edges[trim.edge_index]
    crv3d = b.m_curves_3d[edge.curve_3d_index]
    crv2d = b.m_curves_2d[trim.curve_2d_index]
    print(f"\n[3D curve] order={crv3d.order()} cvs={crv3d.cv_count()} reversed={trim.reversed}")
    for i in range(crv3d.cv_count()):
        cv = crv3d.get_cv(i)
        print(f"  3D[{i}] ({cv[0]:.3f}, {cv[1]:.3f}, {cv[2]:.3f})")
    print(f"[2D UV curve] cvs={crv2d.cv_count()}")
    for i in range(crv2d.cv_count()):
        cv = crv2d.get_cv(i)
        print(f"  UV[{i}] ({cv[0]:.6f}, {cv[1]:.6f})")

print("\n--- CreatePlanarBreps (all faces) ---")
rbreps = _rb._build_with_createplanar(b)
if not rbreps:
    print("  -> None")
else:
    print(f"  -> {len(rbreps)} brep(s)")
    for bi2, rb in enumerate(rbreps):
        bb = rb.GetBoundingBox(False)
        mn = bb.Min
        mx = bb.Max
        valid = "valid" if rb.IsValid else "INVALID"
        print("  brep[" + str(bi2) + "] " + valid + " faces=" + str(rb.Faces.Count) +
              " bbox min=(" + str(round(mn.X,2)) + "," + str(round(mn.Y,2)) + "," + str(round(mn.Z,2)) +
              ") max=(" + str(round(mx.X,2)) + "," + str(round(mx.Y,2)) + "," + str(round(mx.Z,2)) + ")")


mesh = meshes[0]
fk0 = sorted(mesh.face.keys())[0]
print(f"\n[Mesh[0] face[{fk0}] verts]:")
for vk in mesh.face[fk0]:
    p = mesh.vertex[vk].position()
    print(f"  vk={vk}: ({p[0]:.3f}, {p[1]:.3f}, {p[2]:.3f})")