"""Shared Rhino geometry helpers used across wood_nano plugin commands.

Functions
---------
extract_mesh            Rhino mesh (incl. ngons) → (vertices, faces) lists
extract_nurbs_surface   Rhino NURBS surface → control-point/knot tuples
expand_knots            multiplicity/value pairs → flat knot vector
dist_point_to_segment   minimum distance from a point to a segment
get_polyline_points     GUID → list[rg.Point3d]
cross                   cross product of two (x, y, z) tuples
normalize               unit vector from a (x, y, z) tuple
face_normal             Newell normal from a list of rg.Point3d
loft_mesh_to_rhino      session_py Mesh → welded rg.Mesh with ngons
write_plate_userstring  write one UserString to bot/top objects of a plate
ensure_layer            create (or return) a Rhino layer by full path
guid_to_session_polyline  Rhino curve GUID → session_py Polyline (closed)
pl_coords_to_pt3d       session_py Polyline coords → list[rg.Point3d]
"""

import math

import System.Drawing  # type: ignore
import Rhino  # type: ignore
import scriptcontext as sc  # type: ignore


# ── Mesh / surface converters ─────────────────────────────────────────────────

def extract_mesh(rhino_mesh):
    """Convert a Rhino mesh (including ngons) to ``(vertices, faces)`` lists."""
    rhino_mesh.Weld(0.01)
    verts = [[v.X, v.Y, v.Z] for v in rhino_mesh.Vertices]
    ngon_face_indices = set()
    faces = []
    if rhino_mesh.Ngons.Count > 0:
        for i in range(rhino_mesh.Ngons.Count):
            ngon = rhino_mesh.Ngons[i]
            for fi in ngon.FaceIndexList():
                ngon_face_indices.add(fi)
            faces.append(list(ngon.BoundaryVertexIndexList()))
    for i, f in enumerate(rhino_mesh.Faces):
        if i in ngon_face_indices:
            continue
        if f.IsTriangle:
            faces.append([f.A, f.B, f.C])
        else:
            faces.append([f.A, f.B, f.C, f.D])
    return verts, faces


def extract_nurbs_surface(rhino_srf):
    """Extract control points and knots from a Rhino NURBS surface.

    Returns ``(pts, knots_u, knots_v, degree_u, degree_v, n_u, n_v)`` ready to
    pass directly to any ``*_from_surface`` or ``*_nurbs`` wood_nano function.
    """
    ns = rhino_srf.ToNurbsSurface()
    n_u, n_v = ns.Points.CountU, ns.Points.CountV
    pts = []
    for i in range(n_u):
        for j in range(n_v):
            _, p = ns.Points.GetPoint(i, j)
            pts.append([p.X, p.Y, p.Z])
    knots_u = [ns.KnotsU[i] for i in range(ns.KnotsU.Count)]
    knots_v = [ns.KnotsV[j] for j in range(ns.KnotsV.Count)]
    return pts, knots_u, knots_v, ns.Degree(0), ns.Degree(1), n_u, n_v


def expand_knots(mults, vals):
    """Expand knot multiplicity/value pairs into a flat knot vector.

    Strips the first and last entry to match the OpenNURBS convention expected
    by wood_nano's NURBS surface functions.
    """
    knots = []
    for m, v in zip(mults, vals):
        knots.extend([v] * m)
    return knots[1:-1]


# ── Geometry math utilities ───────────────────────────────────────────────────

def dist_point_to_segment(pt, a, b):
    """Return minimum distance from point pt to segment a–b (rg.Point3d)."""
    abx = b.X - a.X; aby = b.Y - a.Y; abz = b.Z - a.Z
    apx = pt.X - a.X; apy = pt.Y - a.Y; apz = pt.Z - a.Z
    ab2 = abx*abx + aby*aby + abz*abz
    if ab2 < 1e-20:
        return math.sqrt(apx*apx + apy*apy + apz*apz)
    t = max(0.0, min(1.0, (apx*abx + apy*aby + apz*abz) / ab2))
    dx = apx - t*abx; dy = apy - t*aby; dz = apz - t*abz
    return math.sqrt(dx*dx + dy*dy + dz*dz)


def get_polyline_points(guid):
    """Return list[rg.Point3d] from a curve GUID, or None on failure."""
    if guid is None:
        return None
    obj = sc.doc.Objects.FindId(guid)
    if obj is None:
        return None
    ok, rh_pl = obj.Geometry.TryGetPolyline()
    if not ok or rh_pl is None:
        return None
    return list(rh_pl)


def cross(a, b):
    """Cross product of two (x, y, z) tuples."""
    return (a[1]*b[2] - a[2]*b[1],
            a[2]*b[0] - a[0]*b[2],
            a[0]*b[1] - a[1]*b[0])


def normalize(v):
    """Normalize a (x, y, z) tuple to unit length."""
    L = math.sqrt(v[0]**2 + v[1]**2 + v[2]**2)
    return (v[0]/L, v[1]/L, v[2]/L) if L > 1e-12 else v


def face_normal(pts):
    """Newell normal from a list of rg.Point3d (open or closed ring)."""
    n = len(pts)
    nx = ny = nz = 0.0
    for i in range(n):
        j = (i + 1) % n
        ax, ay, az = pts[i].X, pts[i].Y, pts[i].Z
        bx, by, bz = pts[j].X, pts[j].Y, pts[j].Z
        nx += (ay - by) * (az + bz)
        ny += (az - bz) * (ax + bx)
        nz += (ax - bx) * (ay + by)
    L = math.sqrt(nx*nx + ny*ny + nz*nz)
    return (nx/L, ny/L, nz/L) if L > 1e-12 else None


# ── session_py ↔ Rhino converters ────────────────────────────────────────────

def loft_mesh_to_rhino(mesh):
    """Convert a session_py Mesh to a welded Rhino.Geometry.Mesh.

    Side faces (quads/tris) are added directly.  Cap faces with CDT
    triangulation are added as triangles then wrapped in an Ngon so Rhino
    hides the internal triangulation edges visually.
    """
    vkeys = sorted(mesh.vertex.keys())
    vkey_to_idx = {vk: i for i, vk in enumerate(vkeys)}
    rmesh = Rhino.Geometry.Mesh()
    for vk in vkeys:
        v = mesh.vertex[vk]
        rmesh.Vertices.Add(v.x, v.y, v.z)
    tri = mesh.triangulation or {}
    holes = mesh.face_holes or {}
    for fk in sorted(mesh.face.keys()):
        stored = tri.get(fk)
        if stored:
            hole_rings = holes.get(fk, [])
            all_vks = list(mesh.face[fk]) + [vk for ring in hole_rings for vk in ring]
            local = {vk: vkey_to_idx[vk] for vk in all_vks if vk in vkey_to_idx}
            fi_start = rmesh.Faces.Count
            for t in stored:
                a, b, c = local.get(t[0]), local.get(t[1]), local.get(t[2])
                if a is not None and b is not None and c is not None:
                    rmesh.Faces.AddFace(a, b, c)
            fi_end = rmesh.Faces.Count
            outer_idx = [vkey_to_idx[vk] for vk in mesh.face[fk] if vk in vkey_to_idx]
            if len(outer_idx) >= 3 and fi_end > fi_start:
                rmesh.Ngons.AddNgon(
                    Rhino.Geometry.MeshNgon.Create(outer_idx, list(range(fi_start, fi_end)))
                )
        else:
            vks = mesh.face[fk]
            idx = [vkey_to_idx[vk] for vk in vks]
            if len(idx) == 3:
                rmesh.Faces.AddFace(idx[0], idx[1], idx[2])
            elif len(idx) == 4:
                rmesh.Faces.AddFace(idx[0], idx[1], idx[2], idx[3])
    rmesh.Normals.ComputeNormals()
    return rmesh


def guid_to_session_polyline(guid):
    """Read a Rhino curve object by GUID and return a session_py Polyline.

    Rhino stores closed polylines as open PolylineCurves (consecutive duplicate
    points are stripped).  WoodElement needs a closed polyline (first == last)
    so that n_sides = len(pts) - 1 is correct.  Re-adds the closing point.
    """
    from session_py.point import Point as PyPoint
    from session_py.polyline import Polyline as PyPolyline
    if guid is None:
        return None
    obj = sc.doc.Objects.FindId(guid)
    if obj is None:
        return None
    crv = obj.Geometry
    ok, rh_pl = crv.TryGetPolyline()
    if not ok or rh_pl is None:
        return None
    pts = [PyPoint(float(pt.X), float(pt.Y), float(pt.Z)) for pt in rh_pl]
    if len(pts) < 2:
        return None
    p0, pN = pts[0], pts[-1]
    if p0.x != pN.x or p0.y != pN.y or p0.z != pN.z:
        pts.append(PyPoint(p0.x, p0.y, p0.z))
    return PyPolyline(pts)


def pl_coords_to_pt3d(pl):
    """Convert session_py Polyline to list of rg.Point3d, closing point stripped."""
    c = pl.coords
    pts = [Rhino.Geometry.Point3d(c[i], c[i+1], c[i+2]) for i in range(0, len(c), 3)]
    if len(pts) >= 2:
        p0, pn = pts[0], pts[-1]
        if p0.DistanceTo(pn) < 1e-6:
            pts = pts[:-1]
    return pts


# ── Rhino document utilities ──────────────────────────────────────────────────

def write_plate_userstring(plate_map, plate_id, key, value_str):
    """Write one UserString to bot/top objects of a plate.

    Operates only on the GUIDs collected during selection (plate_map) so that
    other copies of the same layout with identical plate_id values are not
    accidentally updated.
    """
    roles = plate_map.get(plate_id, {})
    for role in ("bot", "top"):
        guid = roles.get(role)
        if guid is None:
            continue
        obj = sc.doc.Objects.FindId(guid)
        if obj is None:
            continue
        obj.Attributes.SetUserString(key, value_str)
        obj.CommitChanges()


def ensure_layer(full_path, parent_path, rgb, visible):
    """Create (or return existing) a Rhino layer by its full path.

    Parameters
    ----------
    full_path : str
        Full layer path, e.g. ``"Parent::Child"``.
    parent_path : str or None
        Full path of the parent layer, or ``None`` for a root layer.
    rgb : tuple[int, int, int]
        Layer colour as (R, G, B).
    visible : bool
        Initial visibility.

    Returns
    -------
    int
        Layer index in ``sc.doc.Layers``.
    """
    idx = sc.doc.Layers.FindByFullPath(full_path, Rhino.RhinoMath.UnsetIntIndex)
    if idx >= 0:
        return idx
    layer = Rhino.DocObjects.Layer()
    layer.Name = full_path.split("::")[-1]
    layer.Color = System.Drawing.Color.FromArgb(*rgb)
    layer.IsVisible = visible
    if parent_path:
        pidx = sc.doc.Layers.FindByFullPath(parent_path, Rhino.RhinoMath.UnsetIntIndex)
        if pidx >= 0:
            layer.ParentLayerId = sc.doc.Layers[pidx].Id
    return sc.doc.Layers.Add(layer)
