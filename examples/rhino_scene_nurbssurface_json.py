#! python3
# venv: session_py

from session_py.reload import reload_all
import session_rhino
reload_all()

from session_rhino.session import Session
from session_py.point import Point
from session_py.line import Line

filepath = r"c:\pc\3_code\code_rust\session\session_data\mesh_quad_tri_loft10_out.pb"
scene = Session.load(filepath)

scene.add(Point(0, 0, 0))
scene.add(Line(0, 0, 0, 10, 0, 0))

scene.draw(delete=True)
