#! python3
# venv: session_py

from session_py.reload import reload_all                                                                                                                                                      
import session_rhino
reload_all()

from session_py.session_config import SESSION_CONFIG
SESSION_CONFIG.explode_mesh_faces = True

from session_rhino.session import Session
filepath = r"C:\brg\code_rust\session\session_data\QuaternionViz.pb"
filepath = r"C:\brg\code_rust\session\session_data\WoodF2F_annen.pb"
# filepath = r"C:\brg\code_rust\session\session_data\WoodF2F_hexbox.pb"
filepath = r"C:\brg\code_rust\session\session_data\WoodF2F_cross_corners.pb"
scene = Session.load(filepath)
scene.draw(delete=True)