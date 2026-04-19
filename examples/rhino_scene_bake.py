#! python3
# venv: session_py
"""
Rhino viewer launcher for every wood dataset produced by main_5.exe.
Uncomment exactly one `filepath = ...` line to view that dataset.
"""

import importlib
import session_rhino.session
importlib.reload(session_rhino.session)
from session_rhino.session import Session

from session_py.session_config import SESSION_CONFIG
SESSION_CONFIG.explode_mesh_faces = True

# ── default (latest-viewed sits at the top; comment others to swap) ───────
# filepath = r"C:\brg\code_rust\session\session_data\WoodF2F_annen.pb"

# ── vidychapel family ─────────────────────────────────────────────────────
# filepath = r"C:\brg\code_rust\session\session_data\WoodF2F_vidy_corner.pb"
# filepath = r"C:\brg\code_rust\session\session_data\WoodF2F_vidy_one_layer.pb"
# filepath = r"C:\brg\code_rust\session\session_data\WoodF2F_vidy_one_axis_two_layers.pb"
# filepath = r"C:\brg\code_rust\session\session_data\WoodF2F_vidy_full.pb"
# filepath = r"C:\brg\code_rust\session\session_data\WoodF2F_vidy_folding.pb"

# ── side-to-side out-of-plane ─────────────────────────────────────────────
# filepath = r"C:\brg\code_rust\session\session_data\WoodF2F_outofplane_box.pb"
# filepath = r"C:\brg\code_rust\session\session_data\WoodF2F_outofplane_tetra.pb"
# filepath = r"C:\brg\code_rust\session\session_data\WoodF2F_outofplane_dodecahedron.pb"
# filepath = r"C:\brg\code_rust\session\session_data\WoodF2F_outofplane_icosahedron.pb"
# filepath = r"C:\brg\code_rust\session\session_data\WoodF2F_outofplane_octahedron.pb"
# filepath = r"C:\brg\code_rust\session\session_data\WoodF2F_hexboxes.pb"

# ── side-to-side in-plane ─────────────────────────────────────────────────
# filepath = r"C:\brg\code_rust\session\session_data\WoodF2F_inplane_butterflies.pb"
# filepath = r"C:\brg\code_rust\session\session_data\WoodF2F_inplane_hexshell.pb"  
# filepath = r"C:\brg\code_rust\session\session_data\WoodF2F_inplane_differentdirections.pb"
filepath = r"C:\brg\code_rust\session\session_data\WoodF2F_inplane_hilti.pb" # no butterflies at a ll, there must be butterflies merged with polylines

# ── simple corners (mixed in/out-of-plane) ────────────────────────────────
# filepath = r"C:\brg\code_rust\session\session_data\WoodF2F_simple_corners.pb"
# filepath = r"C:\brg\code_rust\session\session_data\WoodF2F_simple_corners_combined.pb"
# filepath = r"C:\brg\code_rust\session\session_data\WoodF2F_simple_corners_diff_lengths.pb"

# ── top-to-top / top-to-side ──────────────────────────────────────────────
# filepath = r"C:\brg\code_rust\session\session_data\WoodF2F_top_to_top_pairs.pb"
# filepath = r"C:\brg\code_rust\session\session_data\WoodF2F_top_to_side_box.pb"
# filepath = r"C:\brg\code_rust\session\session_data\WoodF2F_top_to_side_corners.pb"

# ── annen ─────────────────────────────────────────────────────────────────
# filepath = r"C:\brg\code_rust\session\session_data\WoodF2F_annen_box.pb"
# filepath = r"C:\brg\code_rust\session\session_data\WoodF2F_annen_box_pair.pb"
# filepath = r"C:\brg\code_rust\session\session_data\WoodF2F_annen_corner.pb"

# ── cross family ──────────────────────────────────────────────────────────
# filepath = r"C:\brg\code_rust\session\session_data\WoodF2F_cross_corners.pb"
# filepath = r"C:\brg\code_rust\session\session_data\WoodF2F_cross_vda_corner.pb"
# filepath = r"C:\brg\code_rust\session\session_data\WoodF2F_cross_vda_hexshell.pb"
# filepath = r"C:\brg\code_rust\session\session_data\WoodF2F_cross_vda_hexshell_reciprocal.pb"
# filepath = r"C:\brg\code_rust\session\session_data\WoodF2F_cross_vda_shell.pb"
# filepath = r"C:\brg\code_rust\session\session_data\WoodF2F_cross_vda_single_arch.pb"
# filepath = r"C:\brg\code_rust\session\session_data\WoodF2F_cross_and_sides_corner.pb"
# filepath = r"C:\brg\code_rust\session\session_data\WoodF2F_cross_brussels_sports_tower.pb" # no joint merged
# filepath = r"C:\brg\code_rust\session\session_data\WoodF2F_cross_ibois_pavilion.pb"
# filepath = r"C:\brg\code_rust\session\session_data\WoodF2F_cross_square_reciprocal_iseya.pb"
# filepath = r"C:\brg\code_rust\session\session_data\WoodF2F_cross_square_reciprocal_two_sides.pb"

# ── hex / VDA / misc ──────────────────────────────────────────────────────
# filepath = r"C:\brg\code_rust\session\session_data\WoodF2F_hexbox_and_corner.pb"
# filepath = r"C:\brg\code_rust\session\session_data\WoodF2F_hex_block_rossiniere.pb" # smth is completey wrong
# filepath = r"C:\brg\code_rust\session\session_data\WoodF2F_vda_floor_0.pb"
# filepath = r"C:\brg\code_rust\session\session_data\WoodF2F_vda_floor_2.pb"

# ── beams ─────────────────────────────────────────────────────────────────
filepath = r"C:\brg\code_rust\session\session_data\WoodF2F_phanomema_node.pb" # nothing is implemented at all empty dataset


scene = Session.load(filepath)
scene.draw(delete=True)
