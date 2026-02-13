import Rhino
import System


def _fan_triangulate(face):
    """Triangulate a polygon face using fan triangulation from vertex 0."""
    tris = []
    for i in range(1, len(face) - 1):
        tris.append((int(face[0]), int(face[i]), int(face[i + 1])))
    return tris


def to_rhino(mesh):
    rmesh = Rhino.Geometry.Mesh()
    verts, faces = mesh.to_vertices_and_faces()
    for v in verts:
        rmesh.Vertices.Add(float(v[0]), float(v[1]), float(v[2]))
    ngon_data = []
    for f in faces:
        n = len(f)
        if n == 3:
            rmesh.Faces.AddFace(int(f[0]), int(f[1]), int(f[2]))
        elif n == 4:
            rmesh.Faces.AddFace(int(f[0]), int(f[1]), int(f[2]), int(f[3]))
        elif n >= 5:
            start_fi = rmesh.Faces.Count
            tris = _fan_triangulate(f)
            for t in tris:
                rmesh.Faces.AddFace(t[0], t[1], t[2])
            end_fi = rmesh.Faces.Count
            ngon_data.append(([int(v) for v in f], list(range(start_fi, end_fi))))
    if len(mesh.pointcolors) > 0 and len(mesh.pointcolors) == len(verts):
        for c in mesh.pointcolors:
            rmesh.VertexColors.Add(int(c[0]), int(c[1]), int(c[2]))
    rmesh.Normals.ComputeNormals()
    rmesh.Compact()
    for vi_list, fi_list in ngon_data:
        ngon = Rhino.Geometry.MeshNgon.Create(vi_list, fi_list)
        rmesh.Ngons.AddNgon(ngon)
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
