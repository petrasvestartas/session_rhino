#! python3
# venv: session_py
                                                                                                                                                                          

from session_py.reload import reload_all
import session_rhino
reload_all()


from session_rhino.session import Session

filepath = r"C:\brg\code_rust\session\session_data\WoodStep4.pb"
scene = Session.load(filepath)
scene.draw(delete=True)
                                