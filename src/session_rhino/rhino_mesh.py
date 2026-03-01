import Rhino
import System


def _is_colored(colors):
    return any(c[0] != 255 or c[1] != 255 or c[2] != 255 for c in colors)


def _to_rhino_face_colors(mesh):
    rmesh = Rhino.Geometry.Mesh()
    face_keys = sorted(mesh.face.keys())
    f_offset = 0
    for fi, fk in enumerate(face_keys):
        vks = mesh.face[fk]
        n = len(vks)
        fc = mesh.facecolors[fi] if fi < len(mesh.facecolors) else None
        base = rmesh.Vertices.Count
        if n <= 4:
            for vk in vks:
                pt = mesh.vertex[vk].position()
                rmesh.Vertices.Add(float(pt[0]), float(pt[1]), float(pt[2]))
                if fc is not None:
                    rmesh.VertexColors.Add(int(fc[0]), int(fc[1]), int(fc[2]))
            if n == 3:
                rmesh.Faces.AddFace(base, base + 1, base + 2)
                rmesh.Ngons.AddNgon(Rhino.Geometry.MeshNgon.Create(
                    list(range(base, base + 3)), [f_offset]))
                f_offset += 1
            else:
                rmesh.Faces.AddFace(base, base + 1, base + 2, base + 3)
                rmesh.Ngons.AddNgon(Rhino.Geometry.MeshNgon.Create(
                    list(range(base, base + 4)), [f_offset]))
                f_offset += 1
        else:
            cx, cy, cz = 0.0, 0.0, 0.0
            for vk in vks:
                pt = mesh.vertex[vk].position()
                cx += float(pt[0]); cy += float(pt[1]); cz += float(pt[2])
            cx /= n; cy /= n; cz /= n
            for vk in vks:
                pt = mesh.vertex[vk].position()
                rmesh.Vertices.Add(float(pt[0]), float(pt[1]), float(pt[2]))
                if fc is not None:
                    rmesh.VertexColors.Add(int(fc[0]), int(fc[1]), int(fc[2]))
            center_idx = rmesh.Vertices.Count
            rmesh.Vertices.Add(cx, cy, cz)
            if fc is not None:
                rmesh.VertexColors.Add(int(fc[0]), int(fc[1]), int(fc[2]))
            start_fi = f_offset
            for i in range(n):
                rmesh.Faces.AddFace(base + i, base + (i + 1) % n, center_idx)
                f_offset += 1
            ngon_verts = list(range(base, base + n))
            ngon_faces = list(range(start_fi, f_offset))
            rmesh.Ngons.AddNgon(Rhino.Geometry.MeshNgon.Create(ngon_verts, ngon_faces))
    rmesh.Compact()
    if rmesh.Ngons.Count > 0:
        rmesh.UnifyNormals()
    rmesh.FaceNormals.ComputeFaceNormals()
    rmesh.Normals.ComputeNormals()
    return rmesh


def to_rhino(mesh):
    any_vc = _is_colored(mesh.pointcolors)
    any_fc = _is_colored(mesh.facecolors)

    if any_fc and not any_vc:
        return _to_rhino_face_colors(mesh)

    rmesh = Rhino.Geometry.Mesh()
    verts, faces = mesh.to_vertices_and_faces()
    for v in verts:
        rmesh.Vertices.Add(float(v[0]), float(v[1]), float(v[2]))

    f_offset = 0

    for f in faces:
        n = len(f)
        if n == 3:
            rmesh.Faces.AddFace(int(f[0]), int(f[1]), int(f[2]))
            rmesh.Ngons.AddNgon(Rhino.Geometry.MeshNgon.Create(
                [int(x) for x in f], [f_offset]))
            f_offset += 1
        elif n == 4:
            rmesh.Faces.AddFace(int(f[0]), int(f[1]), int(f[2]), int(f[3]))
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

    if any_vc and len(mesh.pointcolors) == len(verts):
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
    color = None
    if _is_colored(mesh.facecolors):
        color = next((c for c in mesh.facecolors if _is_colored([c])), None)
    elif _is_colored(mesh.linecolors):
        color = next((c for c in mesh.linecolors if _is_colored([c])), None)
    elif _is_colored(mesh.pointcolors):
        color = next((c for c in mesh.pointcolors if _is_colored([c])), None)
    if color is not None:
        attr.ObjectColor = System.Drawing.Color.FromArgb(color[3], color[0], color[1], color[2])
        attr.ColorSource = Rhino.DocObjects.ObjectColorSource.ColorFromObject
        doc.Objects.ModifyAttributes(guid, attr, True)


def add(obj_or_list, **kwargs):
    from session_py.primitives import Primitives
    from session_py.line import Line
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
        edges = mesh.edges()
        for i, (u, v) in enumerate(edges):
            lc = mesh.linecolors[i] if i < len(mesh.linecolors) else None
            if lc is None or not _is_colored([lc]):
                continue
            w = mesh.widths[i] if i < len(mesh.widths) else 1.0
            start = mesh.vertex[u].position()
            end = mesh.vertex[v].position()
            line = Line(start[0], start[1], start[2], end[0], end[1], end[2])
            pipe = Primitives.cylinder_mesh(line, w)
            if lc is not None:
                for j in range(len(pipe.facecolors)):
                    pipe.facecolors[j] = lc
            rpipe = to_rhino(pipe)
            pipe_guid = doc.Objects.AddMesh(rpipe)
            if pipe_guid != System.Guid.Empty:
                _apply_attributes(doc, pipe_guid, pipe)
    doc.Views.Redraw()
    return guids
