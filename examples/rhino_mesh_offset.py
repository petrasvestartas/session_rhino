#! python3
# venv: session_py

import importlib
import session_rhino.session
importlib.reload(session_rhino.session)
from session_rhino.session import Session

filepath = r"C:\pc\3_code\code_rust\session\session_data\mesh_offset_panels.pb"

scene = Session.load(filepath)
scene.draw(delete=True)
