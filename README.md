# session_rhino

RhinoCommon converters for `session_py` geometry. Runs inside Rhino 8 Python 3.

## Install

```bash
./rhino.sh
```

## Usage

```python
from session_py import Point
from session_py import NurbsCurve
from session_rhino.session import Session

session = Session()

# points
session.add(Point(1, 2, 3))
session.add([Point(0, 0, 0), Point(1, 0, 0)])

# nurbs curve
pts = [Point(0, 0, 0), Point(1, 1, 0), Point(2, 0, 0), Point(3, 1, 0)]
curve = NurbsCurve.create(periodic=False, degree=2, points=pts)
session.add(curve)

# divide curve and add points
divided, params = curve.divide_by_count(10, True)
session.add(divided)

# perpendicular frames along curve
frames = curve.get_perpendicular_planes(10)
session.add(frames, scale=0.2)

session.draw(delete=True)
```

## Modules

| Module | session_py | RhinoCommon |
|--------|-----------|-------------|
| `rhino_point` | Point | Point3d |
| `rhino_line` | Line | Line |
| `rhino_plane` | Plane | Plane |
| `rhino_mesh` | Mesh | Mesh |
| `rhino_nurbscurve` | NurbsCurve | NurbsCurve |

## Hot reload

```python
from session_py.reload import reload_all
reload_all()
```
