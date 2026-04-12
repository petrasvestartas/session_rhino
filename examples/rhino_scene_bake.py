#! python3
# venv: session_py

import importlib
import session_rhino.session
importlib.reload(session_rhino.session)
from session_rhino.session import Session

from session_py.session_config import SESSION_CONFIG
SESSION_CONFIG.explode_mesh_faces = True

filepath = r"C:\brg\code_rust\session\session_data\WoodF2F_outofplane_box.pb"
filepath = r"C:\brg\code_rust\session\session_data\WoodF2F_annen.pb"
# filepath = r"C:\brg\code_rust\session\session_data\WoodF2F_cross_corners.pb"
# filepath = r"C:\brg\code_rust\session\session_data\WoodF2F_inplane_butterflies.pb"
# filepath = r"C:\brg\code_rust\session\session_data\WoodF2F_cross_vda_corner.pb"
# filepath = r"C:\brg\code_rust\session\session_data\WoodF2F_hexbox.pb"
filepath = r"C:\brg\code_rust\session\session_data\WoodF2F_vidy_corner.pb"

scene = Session.load(filepath)
scene.draw(delete=True)