#! python3
# venv: session_py
# Inputs: top_brep (Brep), bot_brep (Brep), output_path (str) e.g. C:\pc\3_code\code_rust\session\session_data\boundaries.pb
# Outputs: outer0 (list), outer1 (list)
import Rhino
from session_py import Polyline, Objects


def rh_polyline_to_session(rh_pl, name):
    coords = []
    for pt in rh_pl:
        coords.extend([pt.X, pt.Y, pt.Z])
    pl = Polyline.from_coords(coords)
    pl.name = name
    return pl


def clean_polyline(pl, tol):
    pts = list(pl)
    # step 1: remove consecutive near-duplicates
    cleaned = [pts[0]]
    for i in range(1, len(pts)):
        if pts[i].DistanceTo(cleaned[-1]) > tol:
            cleaned.append(pts[i])
    # step 2: iteratively remove collinear midpoints
    zt2 = 1e-24
    tol2 = tol * tol
    changed = True
    while changed:
        changed = False
        m = len(cleaned)
        if m < 3:
            break
        out = [cleaned[0]]
        for i in range(1, m - 1):
            p, nx = cleaned[i - 1], cleaned[i + 1]
            vx = nx.X - p.X; vy = nx.Y - p.Y; vz = nx.Z - p.Z
            wx = cleaned[i].X - p.X; wy = cleaned[i].Y - p.Y; wz = cleaned[i].Z - p.Z
            cx = vy*wz - vz*wy; cy = vz*wx - vx*wz; cz = vx*wy - vy*wx
            v2 = vx*vx + vy*vy + vz*vz
            if v2 < zt2 or cx*cx + cy*cy + cz*cz < tol2 * v2:
                changed = True
            else:
                out.append(cleaned[i])
        out.append(cleaned[-1])
        cleaned = out
    # step 3: close
    if len(cleaned) >= 2 and cleaned[-1].DistanceTo(cleaned[0]) > tol:
        cleaned.append(cleaned[0])
    return Rhino.Geometry.Polyline(cleaned)


def brep_outlines(brep, tol=Rhino.RhinoDoc.ActiveDoc.ModelAbsoluteTolerance):
    outer = []
    holes = []
    if brep and isinstance(brep, Rhino.Geometry.Brep):
        for face in brep.Faces:
            for loop in face.Loops:
                crv = loop.To3dCurve()
                result, polyline = crv.TryGetPolyline()
                if not result:
                    continue
                polyline = clean_polyline(polyline, tol)
                if loop.LoopType == Rhino.Geometry.BrepLoopType.Outer:
                    outer.append(polyline)
                else:
                    holes.append(polyline)
    return outer, holes


outer0, holes0 = brep_outlines(top_brep)
outer1, holes1 = brep_outlines(bot_brep)

from pathlib import Path

if output_path:
    out = Path(output_path.strip())
    out.parent.mkdir(parents=True, exist_ok=True)
    obj = Objects()
    for i, rh_pl in enumerate(outer0):
        obj.polylines.append(rh_polyline_to_session(rh_pl, "top_face{}".format(i)))
    for i, rh_pl in enumerate(outer1):
        obj.polylines.append(rh_polyline_to_session(rh_pl, "bot_face{}".format(i)))
    obj.pb_dump(str(out))
