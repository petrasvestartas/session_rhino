#! python3
# venv: session_py


from session_py.reload import reload_all
import session_rhino
reload_all()



from session_rhino.session import Session
from session_py.session import Session as PySession
from session_rhino.rhino_mesh import to_rhino
import Rhino
import System

filepath = r"C:\brg\code_rust\session\session_data\Xform.pb"

data = PySession.pb_load(filepath)
meshes = list(data.objects.meshes)


scene = Session.load(filepath)
scene.draw(delete=True)

