import Rhino
import System


def to_rhino(mesh):
    rmesh = Rhino.Geometry.Mesh()
    verts, faces = mesh.to_vertices_and_faces()
    for v in verts:
        rmesh.Vertices.Add(float(v[0]), float(v[1]), float(v[2]))

    v_offset = 0
    f_offset = 0

    for f in faces:
        n = len(f)
        if n == 3:
            rmesh.Faces.AddFace(int(f[0]), int(f[1]), int(f[2]))
            rmesh.Ngons.AddNgon(Rhino.Geometry.MeshNgon.Create(
                [int(x) for x in f], [f_offset]))
            f_offset += 1
        elif n == 4:
            rmesh.Faces.AddFace(int(f[3]), int(f[2]), int(f[1]), int(f[0]))
            rmesh.Ngons.AddNgon(Rhino.Geometry.MeshNgon.Create(
                [int(x) for x in f], [f_offset]))
            f_offset += 1
        elif n >= 5:
            cx, cy, cz = 0.0, 0.0, 0.0
            for vi in f:
                pt = verts[int(vi)]
                cx += float(pt[0])
                cy += float(pt[1])
                cz += float(pt[2])
            cx /= n
            cy /= n
            cz /= n
            center_idx = rmesh.Vertices.Count
            rmesh.Vertices.Add(cx, cy, cz)

            start_fi = f_offset
            for i in range(n):
                rmesh.Faces.AddFace(int(f[i]), int(f[(i + 1) % n]), center_idx)
                f_offset += 1

            ngon_verts = [int(x) for x in f]
            ngon_faces = list(range(start_fi, f_offset))
            rmesh.Ngons.AddNgon(Rhino.Geometry.MeshNgon.Create(ngon_verts, ngon_faces))

    if len(mesh.pointcolors) > 0 and len(mesh.pointcolors) == len(verts):
        for c in mesh.pointcolors:
            rmesh.VertexColors.Add(int(c[0]), int(c[1]), int(c[2]))

    rmesh.Compact()
    if rmesh.Ngons.Count > 0:
        rmesh.UnifyNormals()
    rmesh.FaceNormals.ComputeFaceNormals()
    rmesh.Normals.ComputeNormals()
    rmesh.Weld(3.14159265358979)
    return rmesh


def _apply_attributes(doc, guid, mesh):
    obj = doc.Objects.Find(guid)
    if obj is None:
        return
    attr = obj.Attributes
    changed = False
    color = None
    if len(mesh.facecolors) > 0:
        color = mesh.facecolors[0]
    elif len(mesh.linecolors) > 0:
        color = mesh.linecolors[0]
    elif len(mesh.pointcolors) > 0:
        color = mesh.pointcolors[0]
    if color is not None:
        attr.ObjectColor = System.Drawing.Color.FromArgb(color[3], color[0], color[1], color[2])
        attr.ColorSource = Rhino.DocObjects.ObjectColorSource.ColorFromObject
        changed = True
    if changed:
        doc.Objects.ModifyAttributes(guid, attr, True)


def add(obj_or_list, **kwargs):
    if not isinstance(obj_or_list, list):
        obj_or_list = [obj_or_list]
    guids = []
    doc = Rhino.RhinoDoc.ActiveDoc
    for mesh in obj_or_list:
        rmesh = to_rhino(mesh)
        guid = doc.Objects.AddMesh(rmesh)
        if guid != System.Guid.Empty:
            _apply_attributes(doc, guid, mesh)
        guids.append(guid)
    doc.Views.Redraw()
    return guids
