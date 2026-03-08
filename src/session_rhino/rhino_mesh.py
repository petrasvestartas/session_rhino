import math

import Rhino
import System


def _is_colored(colors):
    return any(c[0] != 255 or c[1] != 255 or c[2] != 255 for c in colors)


def _project_to_2d(pts3d):
    n = len(pts3d)
    nx = ny = nz = 0.0
    for i in range(n):
        a = pts3d[i]
        b = pts3d[(i + 1) % n]
        nx += (a[1] - b[1]) * (a[2] + b[2])
        ny += (a[2] - b[2]) * (a[0] + b[0])
        nz += (a[0] - b[0]) * (a[1] + b[1])
    mag = math.sqrt(nx*nx + ny*ny + nz*nz)
    if mag < 1e-12:
        return [(p[0], p[1]) for p in pts3d]
    nx /= mag; ny /= mag; nz /= mag
    if abs(nx) < 0.9:
        ax, ay, az = 1.0, 0.0, 0.0
    else:
        ax, ay, az = 0.0, 1.0, 0.0
    dot = ax*nx + ay*ny + az*nz
    ux = ax - dot*nx; uy = ay - dot*ny; uz = az - dot*nz
    um = math.sqrt(ux*ux + uy*uy + uz*uz)
    ux /= um; uy /= um; uz /= um
    vx = ny*uz - nz*uy
    vy = nz*ux - nx*uz
    vz = nx*uy - ny*ux
    return [(p[0]*ux + p[1]*uy + p[2]*uz, p[0]*vx + p[1]*vy + p[2]*vz) for p in pts3d]


def _ngon(verts, faces):
    av = System.Array.CreateInstance(System.Int32, len(verts))
    af = System.Array.CreateInstance(System.Int32, len(faces))
    for i, v in enumerate(verts):
        av[i] = int(v)
    for i, f in enumerate(faces):
        af[i] = int(f)
    return Rhino.Geometry.MeshNgon.Create(av, af)


def _to_rhino_face_colors(mesh):
    rmesh = Rhino.Geometry.Mesh()
    face_keys = sorted(mesh.face.keys())
    f_offset = 0
    for fi, fk in enumerate(face_keys):
        vks = mesh.face[fk]
        n = len(vks)
        fc = mesh.facecolors[fi] if fi < len(mesh.facecolors) else None
        base = rmesh.Vertices.Count
        for vk in vks:
            pt = mesh.vertex[vk].position()
            rmesh.Vertices.Add(float(pt[0]), float(pt[1]), float(pt[2]))
            if fc is not None:
                rmesh.VertexColors.Add(int(fc[0]), int(fc[1]), int(fc[2]))
        stored = mesh.triangulation.get(fk)
        if stored is not None and len(stored) >= n - 2:
            if n == 3:
                rmesh.Faces.AddFace(base, base + 1, base + 2)
                rmesh.Ngons.AddNgon(_ngon(range(base, base + 3), [f_offset]))
                f_offset += 1
            elif n == 4:
                vk_to_local = {vk: j for j, vk in enumerate(vks)}
                start_fi = f_offset
                for t in stored:
                    rmesh.Faces.AddFace(
                        base + vk_to_local[t[0]],
                        base + vk_to_local[t[1]],
                        base + vk_to_local[t[2]],
                    )
                    f_offset += 1
                rmesh.Ngons.AddNgon(_ngon(range(base, base + 4), range(start_fi, f_offset)))
            else:
                vk_to_local = {vk: j for j, vk in enumerate(vks)}
                start_fi = f_offset
                for t in stored:
                    rmesh.Faces.AddFace(base + vk_to_local[t[0]], base + vk_to_local[t[1]], base + vk_to_local[t[2]])
                    f_offset += 1
                rmesh.Ngons.AddNgon(_ngon(range(base, base + n), range(start_fi, f_offset)))
        elif n == 3:
            rmesh.Faces.AddFace(base, base + 1, base + 2)
            rmesh.Ngons.AddNgon(_ngon(range(base, base + 3), [f_offset]))
            f_offset += 1
        elif n == 4:
            rmesh.Faces.AddFace(base, base + 1, base + 2, base + 3)
            rmesh.Ngons.AddNgon(_ngon(range(base, base + 4), [f_offset]))
            f_offset += 1
        else:
            from session_py.trimesh_cdt import cdt_triangulate as _cdt
            start_fi = f_offset
            pts3d = [mesh.vertex[vk].position() for vk in vks]
            cdt_tris = _cdt(_project_to_2d(pts3d))
            if cdt_tris:
                for t in cdt_tris:
                    rmesh.Faces.AddFace(base + t[0], base + t[1], base + t[2])
                    f_offset += 1
            else:
                for i in range(1, n - 1):
                    rmesh.Faces.AddFace(base, base + i, base + i + 1)
                    f_offset += 1
            rmesh.Ngons.AddNgon(_ngon(range(base, base + n), range(start_fi, f_offset)))
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
        fk = face_keys[fi] if fi < len(face_keys) else None
        stored = mesh.triangulation.get(fk) if fk is not None else None
        if stored is not None and len(stored) >= n - 2:
            if n == 3:
                rmesh.Faces.AddFace(int(f[0]), int(f[1]), int(f[2]))
                f_offset += 1
            elif n == 4:
                start_fi = f_offset
                for t in stored:
                    rmesh.Faces.AddFace(vkey_to_idx[t[0]], vkey_to_idx[t[1]], vkey_to_idx[t[2]])
                    f_offset += 1
                rmesh.Ngons.AddNgon(_ngon(f, range(start_fi, f_offset)))
            else:
                start_fi = f_offset
                for t in stored:
                    rmesh.Faces.AddFace(vkey_to_idx[t[0]], vkey_to_idx[t[1]], vkey_to_idx[t[2]])
                    f_offset += 1
                rmesh.Ngons.AddNgon(_ngon(f, range(start_fi, f_offset)))
        elif n == 3:
            rmesh.Faces.AddFace(int(f[0]), int(f[1]), int(f[2]))
            f_offset += 1
        elif n == 4:
            rmesh.Faces.AddFace(int(f[0]), int(f[1]), int(f[2]), int(f[3]))
            f_offset += 1
        else:
            from session_py.trimesh_cdt import cdt_triangulate as _cdt
            start_fi = f_offset
            pts3d = [verts[int(idx)] for idx in f]
            cdt_tris = _cdt(_project_to_2d(pts3d))
            if cdt_tris:
                for t in cdt_tris:
                    rmesh.Faces.AddFace(int(f[t[0]]), int(f[t[1]]), int(f[t[2]]))
                    f_offset += 1
            else:
                for i in range(1, n - 1):
                    rmesh.Faces.AddFace(int(f[0]), int(f[i]), int(f[i + 1]))
                    f_offset += 1
            rmesh.Ngons.AddNgon(_ngon(f, range(start_fi, f_offset)))

    if use_vc and len(mesh.pointcolors) == len(verts):
        for c in mesh.pointcolors:
            rmesh.VertexColors.Add(int(c[0]), int(c[1]), int(c[2]))

    if any_lc and not use_fc and not use_vc:
        rmesh.Weld(3.14159265358979)

    if rmesh.Ngons.Count > 0:
        rmesh.UnifyNormals()
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
