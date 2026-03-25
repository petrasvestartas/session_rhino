import math
from concurrent.futures import ThreadPoolExecutor

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


def _pt3d_array(vks, vertex_map):
    arr = System.Array.CreateInstance(Rhino.Geometry.Point3d, len(vks))
    for i, vk in enumerate(vks):
        pt = vertex_map[vk].position()
        arr[i] = Rhino.Geometry.Point3d(float(pt[0]), float(pt[1]), float(pt[2]))
    return arr


def _set_vertex_colors(rmesh, vc_list):
    carr = System.Array.CreateInstance(System.Drawing.Color, len(vc_list))
    for i, c in enumerate(vc_list):
        carr[i] = System.Drawing.Color.FromArgb(255, int(c[0]), int(c[1]), int(c[2]))
    rmesh.VertexColors.SetColors(carr)


def _to_rhino_face_colors(mesh):
    rmesh = Rhino.Geometry.Mesh()
    face_keys = sorted(mesh.face.keys())
    f_offset = 0
    for fi, fk in enumerate(face_keys):
        vks = mesh.face[fk]
        n = len(vks)
        fc = mesh.facecolors[fi] if fi < len(mesh.facecolors) else (255, 255, 255)
        base = rmesh.Vertices.Count
        rmesh.Vertices.AddVertices(_pt3d_array(vks, mesh.vertex))
        for _ in range(n):
            rmesh.VertexColors.Add(int(fc[0]), int(fc[1]), int(fc[2]))
        stored = mesh.triangulation.get(fk)
        if stored is not None and len(stored) > 0:
            if n == 3:
                vk_to_local = {vk: j for j, vk in enumerate(vks)}
                t = stored[0]
                rmesh.Faces.AddFace(base + vk_to_local[t[0]], base + vk_to_local[t[1]], base + vk_to_local[t[2]])
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
                hole_rings = mesh.face_holes.get(fk, [])
                extra_vks = [vk for ring in hole_rings for vk in ring]
                all_vks = list(vks) + extra_vks
                if extra_vks:
                    rmesh.Vertices.AddVertices(_pt3d_array(extra_vks, mesh.vertex))
                    for _ in range(len(extra_vks)):
                        rmesh.VertexColors.Add(int(fc[0]), int(fc[1]), int(fc[2]))
                vk_to_local = {vk: j for j, vk in enumerate(all_vks)}
                start_fi = f_offset
                for t in stored:
                    rmesh.Faces.AddFace(base + vk_to_local[t[0]], base + vk_to_local[t[1]], base + vk_to_local[t[2]])
                    f_offset += 1
                rmesh.Ngons.AddNgon(_ngon(range(base, base + len(all_vks)), range(start_fi, f_offset)))
        elif n == 3:
            rmesh.Faces.AddFace(base, base + 1, base + 2)
            rmesh.Ngons.AddNgon(_ngon(range(base, base + 3), [f_offset]))
            f_offset += 1
        elif n == 4:
            rmesh.Faces.AddFace(base, base + 1, base + 2, base + 3)
            rmesh.Ngons.AddNgon(_ngon(range(base, base + 4), [f_offset]))
            f_offset += 1
        else:
            from session_py.remesh_cdt import cdt_triangulate as _cdt
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
    # if rmesh.Ngons.Count > 0:
    #     rmesh.UnifyNormals()
    rmesh.FaceNormals.ComputeFaceNormals()
    rmesh.Normals.ComputeNormals()
    return rmesh


def _to_rhino_welded_tri(mesh):
    from session_py.mesh import ColorMode
    rmesh = Rhino.Geometry.Mesh()
    sorted_vkeys = sorted(mesh.vertex.keys())
    vkey_to_seq = {vk: i for i, vk in enumerate(sorted_vkeys)}
    # Deduplicate by exact position — merges coincident vertices (e.g. pole singularities)
    pos_to_rhino_idx = {}
    unique_vkeys = []
    vkey_to_idx = {}
    for vk in sorted_vkeys:
        vd = mesh.vertex[vk]
        pos = (vd[0], vd[1], vd[2])
        if pos not in pos_to_rhino_idx:
            pos_to_rhino_idx[pos] = len(unique_vkeys)
            unique_vkeys.append(vk)
        vkey_to_idx[vk] = pos_to_rhino_idx[pos]
    arr = System.Array.CreateInstance(Rhino.Geometry.Point3d, len(unique_vkeys))
    for i, vk in enumerate(unique_vkeys):
        vd = mesh.vertex[vk]
        arr[i] = Rhino.Geometry.Point3d(vd[0], vd[1], vd[2])
    rmesh.Vertices.AddVertices(arr)
    use_vc = mesh.color_mode == ColorMode.POINTCOLORS
    if use_vc and mesh.pointcolors:
        carr = System.Array.CreateInstance(System.Drawing.Color, len(unique_vkeys))
        for i, vk in enumerate(unique_vkeys):
            seq = vkey_to_seq[vk]
            c = mesh.pointcolors[seq] if seq < len(mesh.pointcolors) else (255, 255, 255)
            carr[i] = System.Drawing.Color.FromArgb(255, int(c[0]), int(c[1]), int(c[2]))
        rmesh.VertexColors.SetColors(carr)
    sorted_fkeys = sorted(mesh.face.keys())
    valid_faces = []
    degen_count = 0
    for fk in sorted_fkeys:
        v0, v1, v2 = mesh.face[fk]
        i0, i1, i2 = vkey_to_idx[v0], vkey_to_idx[v1], vkey_to_idx[v2]
        if i0 == i1 or i1 == i2 or i0 == i2:
            degen_count += 1
            continue
        valid_faces.append(Rhino.Geometry.MeshFace(i0, i1, i2))
    if degen_count:
        print(f"  skipped {degen_count} degenerate faces")
    farr = System.Array.CreateInstance(Rhino.Geometry.MeshFace, len(valid_faces))
    for i, f in enumerate(valid_faces):
        farr[i] = f
    rmesh.Faces.AddFaces(farr)
    rmesh.Compact()
    rmesh.FaceNormals.ComputeFaceNormals()
    rmesh.Normals.ComputeNormals()
    return rmesh


def to_rhino(mesh):
    from session_py.mesh import ColorMode
    from session_py.session_config import SESSION_CONFIG
    mode = mesh.color_mode
    any_lc = _is_colored(mesh.linecolors)

    use_fc = mode == ColorMode.FACECOLORS
    use_vc = mode == ColorMode.POINTCOLORS

    if use_fc:
        return _to_rhino_face_colors(mesh)

    if (not SESSION_CONFIG.explode_mesh_faces
            and not mesh.triangulation
            and not mesh.face_holes
            and mesh.face
            and all(len(v) == 3 for v in mesh.face.values())):
        return _to_rhino_welded_tri(mesh)

    rmesh = Rhino.Geometry.Mesh()
    face_keys = sorted(mesh.face.keys())
    vkey_to_seq = {vk: i for i, vk in enumerate(sorted(mesh.vertex.keys()))}
    f_offset = 0

    for fk in face_keys:
        vks = mesh.face[fk]
        n = len(vks)
        base = rmesh.Vertices.Count
        stored = mesh.triangulation.get(fk)
        if stored is not None and len(stored) > 0:
            hole_rings = mesh.face_holes.get(fk, [])
            all_vks = list(vks) + [vk for ring in hole_rings for vk in ring]
            rmesh.Vertices.AddVertices(_pt3d_array(all_vks, mesh.vertex))
            if use_vc:
                for vk in all_vks:
                    seq = vkey_to_seq[vk]
                    c = mesh.pointcolors[seq] if seq < len(mesh.pointcolors) else (255, 255, 255)
                    rmesh.VertexColors.Add(int(c[0]), int(c[1]), int(c[2]))
            vk_to_local = {vk: j for j, vk in enumerate(all_vks)}
            start_fi = f_offset
            for t in stored:
                rmesh.Faces.AddFace(base + vk_to_local[t[0]], base + vk_to_local[t[1]], base + vk_to_local[t[2]])
                f_offset += 1
            if n >= 3:
                rmesh.Ngons.AddNgon(_ngon(range(base, base + len(all_vks)), range(start_fi, f_offset)))
        elif n == 3:
            rmesh.Vertices.AddVertices(_pt3d_array(vks, mesh.vertex))
            if use_vc:
                for vk in vks:
                    seq = vkey_to_seq[vk]
                    c = mesh.pointcolors[seq] if seq < len(mesh.pointcolors) else (255, 255, 255)
                    rmesh.VertexColors.Add(int(c[0]), int(c[1]), int(c[2]))
            rmesh.Faces.AddFace(base, base + 1, base + 2)
            f_offset += 1
        elif n == 4:
            rmesh.Vertices.AddVertices(_pt3d_array(vks, mesh.vertex))
            if use_vc:
                for vk in vks:
                    seq = vkey_to_seq[vk]
                    c = mesh.pointcolors[seq] if seq < len(mesh.pointcolors) else (255, 255, 255)
                    rmesh.VertexColors.Add(int(c[0]), int(c[1]), int(c[2]))
            rmesh.Faces.AddFace(base, base + 1, base + 2, base + 3)
            f_offset += 1
        else:
            from session_py.remesh_cdt import cdt_triangulate as _cdt
            rmesh.Vertices.AddVertices(_pt3d_array(vks, mesh.vertex))
            if use_vc:
                for vk in vks:
                    seq = vkey_to_seq[vk]
                    c = mesh.pointcolors[seq] if seq < len(mesh.pointcolors) else (255, 255, 255)
                    rmesh.VertexColors.Add(int(c[0]), int(c[1]), int(c[2]))
            pts3d = [mesh.vertex[vk].position() for vk in vks]
            cdt_tris = _cdt(_project_to_2d(pts3d))
            start_fi = f_offset
            if cdt_tris:
                for t in cdt_tris:
                    rmesh.Faces.AddFace(base + t[0], base + t[1], base + t[2])
                    f_offset += 1
            else:
                for i in range(1, n - 1):
                    rmesh.Faces.AddFace(base, base + i, base + i + 1)
                    f_offset += 1
            rmesh.Ngons.AddNgon(_ngon(range(base, base + n), range(start_fi, f_offset)))

    if any_lc and not use_vc:
        rmesh.Weld(3.14159265358979)

    # if rmesh.Ngons.Count > 0:
    #     rmesh.UnifyNormals()
    rmesh.Compact()
    rmesh.FaceNormals.ComputeFaceNormals()
    rmesh.Normals.ComputeNormals()
    return rmesh


def _delete_by_session_guid(doc, session_guid):
    ids = [obj.Id for obj in doc.Objects if obj.Attributes.GetUserString("session_guid") == session_guid]
    for oid in ids:
        doc.Objects.Delete(oid, True)


def add(obj_or_list, layer_idx=0, **kwargs):
    from session_py.primitives import Primitives
    from session_py.line import Line
    from session_py.mesh import ColorMode
    if not isinstance(obj_or_list, list):
        obj_or_list = [obj_or_list]
    doc = Rhino.RhinoDoc.ActiveDoc
    for mesh in obj_or_list:
        if mesh.guid:
            _delete_by_session_guid(doc, mesh.guid)
    if len(obj_or_list) > 1:
        with ThreadPoolExecutor() as ex:
            rmeshes = list(ex.map(to_rhino, obj_or_list))
    else:
        rmeshes = [to_rhino(obj_or_list[0])]
    guids = []
    for mesh, rmesh in zip(obj_or_list, rmeshes):
        attr = Rhino.DocObjects.ObjectAttributes()
        attr.LayerIndex = layer_idx
        attr.Name = mesh.name
        if mesh.guid:
            attr.SetUserString("session_guid", mesh.guid)
        mode = mesh.color_mode
        color = None
        if mode == ColorMode.POINTCOLORS:
            color = next((c for c in mesh.pointcolors if _is_colored([c])), None)
        elif mode == ColorMode.OBJECTCOLOR:
            color = mesh.objectcolor if _is_colored([mesh.objectcolor]) else None
        if color is not None:
            attr.ObjectColor = System.Drawing.Color.FromArgb(color[3], color[0], color[1], color[2])
            attr.ColorSource = Rhino.DocObjects.ObjectColorSource.ColorFromObject
        valid, log = rmesh.IsValidWithLog()
        print(f"mesh '{mesh.name}': rhino valid={valid} verts={rmesh.Vertices.Count} faces={rmesh.Faces.Count}")
        if not valid:
            print(f"  reason: {log.strip()}")
        guid = doc.Objects.AddMesh(rmesh, attr)
        guids.append(guid)
        pipe_guids = []
        if mesh.linecolors and _is_colored(mesh.linecolors):
            for i, (u, v) in enumerate(mesh.edges()):
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
                pipe_attr = Rhino.DocObjects.ObjectAttributes()
                pipe_attr.LayerIndex = layer_idx
                if mesh.guid:
                    pipe_attr.SetUserString("session_guid", mesh.guid)
                pipe_attr.ObjectColor = System.Drawing.Color.FromArgb(lc[3], lc[0], lc[1], lc[2])
                pipe_attr.ColorSource = Rhino.DocObjects.ObjectColorSource.ColorFromObject
                pipe_guid = doc.Objects.AddMesh(rpipe, pipe_attr)
                if pipe_guid != System.Guid.Empty:
                    pipe_guids.append(pipe_guid)
        if pipe_guids and guid != System.Guid.Empty:
            doc.Groups.Add([guid] + pipe_guids)
    return guids
