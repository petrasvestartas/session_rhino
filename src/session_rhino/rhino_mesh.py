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
            for vk in vks:
                pt = mesh.vertex[vk].position()
                rmesh.Vertices.Add(float(pt[0]), float(pt[1]), float(pt[2]))
                if fc is not None:
                    rmesh.VertexColors.Add(int(fc[0]), int(fc[1]), int(fc[2]))
            start_fi = f_offset
            stored = mesh.triangulation.get(fk)
            if stored is not None:
                vk_to_local = {vk: j for j, vk in enumerate(vks)}
                for t in stored:
                    rmesh.Faces.AddFace(base + vk_to_local[t[0]], base + vk_to_local[t[1]], base + vk_to_local[t[2]])
                    f_offset += 1
            else:
                for i in range(1, n - 1):
                    rmesh.Faces.AddFace(base, base + i, base + i + 1)
                    f_offset += 1
            ngon_verts = list(range(base, base + n))
            ngon_faces = list(range(start_fi, f_offset))
            rmesh.Ngons.AddNgon(Rhino.Geometry.MeshNgon.Create(ngon_verts, ngon_faces))
    if rmesh.Ngons.Count > 0:
        rmesh.UnifyNormals()
    rmesh.FaceNormals.ComputeFaceNormals()
    rmesh.Normals.ComputeNormals()
    return rmesh


def to_rhino(mesh):
    from session_py.mesh import ColorMode
    mode = mesh.color_mode
    any_vc = _is_colored(mesh.pointcolors)
    any_fc = _is_colored(mesh.facecolors)
    any_lc = _is_colored(mesh.linecolors)

    use_fc = mode == ColorMode.FACECOLORS
    use_vc = mode == ColorMode.POINTCOLORS

    if use_fc:
        return _to_rhino_face_colors(mesh)

    rmesh = Rhino.Geometry.Mesh()
    verts, faces = mesh.to_vertices_and_faces()
    vkey_to_idx = {vk: i for i, vk in enumerate(sorted(mesh.vertex.keys()))}
    face_keys = sorted(mesh.face.keys())
    for v in verts:
        rmesh.Vertices.Add(float(v[0]), float(v[1]), float(v[2]))

    f_offset = 0

    for fi, f in enumerate(faces):
        n = len(f)
        if n == 3:
            rmesh.Faces.AddFace(int(f[0]), int(f[1]), int(f[2]))
            f_offset += 1
        elif n == 4:
            rmesh.Faces.AddFace(int(f[0]), int(f[1]), int(f[2]), int(f[3]))
            f_offset += 1
        elif n >= 5:
            start_fi = f_offset
            tris = mesh.triangulation.get(face_keys[fi]) if fi < len(face_keys) else None
            if tris is not None:
                for t in tris:
                    rmesh.Faces.AddFace(vkey_to_idx[t[0]], vkey_to_idx[t[1]], vkey_to_idx[t[2]])
                    f_offset += 1
            else:
                for i in range(1, n - 1):
                    rmesh.Faces.AddFace(int(f[0]), int(f[i]), int(f[i + 1]))
                    f_offset += 1
            ngon_verts = [int(x) for x in f]
            ngon_faces = list(range(start_fi, f_offset))
            rmesh.Ngons.AddNgon(Rhino.Geometry.MeshNgon.Create(ngon_verts, ngon_faces))

    if use_vc and len(mesh.pointcolors) == len(verts):
        for c in mesh.pointcolors:
            rmesh.VertexColors.Add(int(c[0]), int(c[1]), int(c[2]))

    if any_lc and not use_fc and not use_vc:
        rmesh.Weld(3.14159265358979)

    rmesh.Compact()
    rmesh.FaceNormals.ComputeFaceNormals()
    rmesh.Normals.ComputeNormals()
    return rmesh


def _apply_attributes(doc, guid, mesh, apply_object_color=False):
    if not apply_object_color:
        return
    obj = doc.Objects.Find(guid)
    if obj is None:
        return
    from session_py.mesh import ColorMode
    mode = mesh.color_mode
    attr = obj.Attributes
    attr.Name = mesh.name
    color = None
    if mode == ColorMode.NONE:
        pass
    elif mode == ColorMode.POINTCOLORS:
        color = next((c for c in mesh.pointcolors if _is_colored([c])), None)
    elif mode == ColorMode.FACECOLORS:
        color = next((c for c in mesh.facecolors if _is_colored([c])), None)
    else:
        color = mesh.objectcolor if _is_colored([mesh.objectcolor]) else None
    if color is not None:
        attr.ObjectColor = System.Drawing.Color.FromArgb(color[3], color[0], color[1], color[2])
        attr.ColorSource = Rhino.DocObjects.ObjectColorSource.ColorFromObject
    doc.Objects.ModifyAttributes(guid, attr, True)


def _delete_by_session_guid(doc, session_guid):
    ids = [obj.Id for obj in doc.Objects if obj.Attributes.GetUserString("session_guid") == session_guid]
    for oid in ids:
        doc.Objects.Delete(oid, True)


def _tag_session_guid(doc, guid, session_guid):
    obj = doc.Objects.Find(guid)
    if obj is None:
        return
    attr = obj.Attributes
    attr.SetUserString("session_guid", session_guid)
    doc.Objects.ModifyAttributes(guid, attr, True)


def add(obj_or_list, **kwargs):
    from session_py.primitives import Primitives
    from session_py.line import Line
    if not isinstance(obj_or_list, list):
        obj_or_list = [obj_or_list]
    guids = []
    doc = Rhino.RhinoDoc.ActiveDoc
    for mesh in obj_or_list:
        if mesh.guid:
            _delete_by_session_guid(doc, mesh.guid)
        rmesh = to_rhino(mesh)
        guid = doc.Objects.AddMesh(rmesh)
        if guid != System.Guid.Empty:
            _apply_attributes(doc, guid, mesh, apply_object_color=True)
            if mesh.guid:
                _tag_session_guid(doc, guid, mesh.guid)
        guids.append(guid)
        pipe_guids = []
        edges = mesh.edges()
        for i, (u, v) in enumerate(edges):
            lc = mesh.linecolors[i] if i < len(mesh.linecolors) else None
            if lc is None or not _is_colored([lc]):
                continue
            w = mesh.widths[i] if i < len(mesh.widths) else 1.0
            start = mesh.vertex[u].position()
            end = mesh.vertex[v].position()
            line = Line(start[0], start[1], start[2], end[0], end[1], end[2])
            pipe = Primitives.capsule_mesh(line, w)
            pipe.set_facecolors([lc] * pipe.number_of_faces())
            rpipe = to_rhino(pipe)
            pipe_guid = doc.Objects.AddMesh(rpipe)
            if pipe_guid != System.Guid.Empty:
                _apply_attributes(doc, pipe_guid, pipe, apply_object_color=True)
                if mesh.guid:
                    _tag_session_guid(doc, pipe_guid, mesh.guid)
                pipe_guids.append(pipe_guid)
        if pipe_guids and guid != System.Guid.Empty:
            group_idx = doc.Groups.Add()
            for g in [guid] + pipe_guids:
                obj = doc.Objects.Find(g)
                if obj is not None:
                    attr = obj.Attributes
                    attr.AddToGroup(group_idx)
                    doc.Objects.ModifyAttributes(g, attr, True)
    doc.Views.Redraw()
    return guids
