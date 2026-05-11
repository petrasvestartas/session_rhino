"""Declarative Rhino command-line input helpers.

Adapted from wood_rui/command.py (petrasvestartas/wood_rui).
Supports float, int, bool, list[str], list[Polyline], list[Mesh], etc.

Usage::

    from session_rhino.rhino_command import process_input

    def run(values, _):
        print(values)

    process_input({
        "cross_section": ([], list[Rhino.Geometry.Polyline]),
        "profile":       ([], list[Rhino.Geometry.Polyline]),
        "thickness":     (15.0, float),
        "chamfer":       (2.0,  float),
        "chamfer_angle": (90.0, float),
    }, callback=run)
"""

import Rhino
from typing import Callable, Dict, Tuple, Union, get_args, get_origin


# ---------------------------------------------------------------------------
# Individual input handlers
# ---------------------------------------------------------------------------

def handle_string_input(option_name):
    """Prompt for a single string value."""
    go = Rhino.Input.Custom.GetString()
    go.SetCommandPrompt(f"Enter value for {option_name}")
    if go.Get() != Rhino.Input.GetResult.String:
        Rhino.RhinoApp.WriteLine("Nothing entered, returning to main menu.")
        return None
    return go.StringResult()


def handle_numbers_input(option_name, hide=True):
    """Prompt for comma-separated floats."""
    go = Rhino.Input.Custom.GetString()
    go.SetCommandPrompt(f"Enter {option_name} as comma-separated values (e.g. 0.0, 1.0, 2.5)")
    if go.Get() != Rhino.Input.GetResult.String:
        Rhino.RhinoApp.WriteLine("Nothing entered, returning to main menu.")
        return []
    try:
        return [float(v.strip()) for v in go.StringResult().split(",")]
    except ValueError:
        Rhino.RhinoApp.WriteLine("Invalid input. Enter numbers separated by commas.")
        return []


def handle_integers_input(option_name, hide=True):
    """Prompt for comma-separated integers."""
    go = Rhino.Input.Custom.GetString()
    go.SetCommandPrompt(f"Enter {option_name} as comma-separated integers (e.g. 1, 2, 3)")
    if go.Get() != Rhino.Input.GetResult.String:
        Rhino.RhinoApp.WriteLine("Nothing entered, returning to main menu.")
        return []
    try:
        return [int(v.strip()) for v in go.StringResult().split(",")]
    except ValueError:
        Rhino.RhinoApp.WriteLine("Invalid input. Enter integers separated by commas.")
        return []


def handle_textdots_input(option_name, hide=True):
    """Select TextDot objects from the Rhino document."""
    go = Rhino.Input.Custom.GetObject()
    go.SetCommandPrompt(f"Select {option_name}")
    go.GeometryFilter = Rhino.DocObjects.ObjectType.TextDot
    go.EnablePreSelect(True, True)
    go.SubObjectSelect = False
    go.DeselectAllBeforePostSelect = False
    go.GetMultiple(1, 0)
    if go.CommandResult() != Rhino.Commands.Result.Success:
        return []
    return [go.Object(i).TextDot() for i in range(go.ObjectCount) if go.Object(i).TextDot()]


def handle_points_input(option_name, hide=True):
    """Select Point objects from the Rhino document."""
    go = Rhino.Input.Custom.GetObject()
    go.SetCommandPrompt(f"Select {option_name}")
    go.GeometryFilter = Rhino.DocObjects.ObjectType.Point
    go.EnablePreSelect(True, True)
    go.SubObjectSelect = False
    go.DeselectAllBeforePostSelect = False
    go.GetMultiple(1, 0)
    if go.CommandResult() != Rhino.Commands.Result.Success:
        return []
    return [go.Object(i).Point().Location for i in range(go.ObjectCount) if go.Object(i).Point()]


def handle_polylines_input(option_name, hide=True):
    """Select curves from Rhino and return them as session_py.Polyline objects."""
    from session_rhino.rhino_polyline import from_rhino
    go = Rhino.Input.Custom.GetObject()
    go.SetCommandPrompt(f"Select {option_name}")
    go.GeometryFilter = Rhino.DocObjects.ObjectType.Curve
    go.EnablePreSelect(True, True)
    go.SubObjectSelect = False
    go.DeselectAllBeforePostSelect = False
    go.GetMultiple(1, 0)
    if go.CommandResult() != Rhino.Commands.Result.Success:
        return []
    polylines = []
    for i in range(go.ObjectCount):
        curve = go.Object(i).Curve()
        if curve:
            ok, pl = curve.TryGetPolyline()
            if ok:
                polylines.append(from_rhino(pl))
            else:
                Rhino.RhinoApp.WriteLine("A selected curve could not be converted to a polyline.")
    return polylines


def handle_lines_input(option_name, hide=True):
    """Select curves and return them as Rhino.Geometry.Line objects."""
    go = Rhino.Input.Custom.GetObject()
    go.SetCommandPrompt(f"Select {option_name}")
    go.GeometryFilter = Rhino.DocObjects.ObjectType.Curve
    go.EnablePreSelect(True, True)
    go.SubObjectSelect = False
    go.DeselectAllBeforePostSelect = False
    go.GetMultiple(1, 0)
    if go.CommandResult() != Rhino.Commands.Result.Success:
        return []
    lines = []
    for i in range(go.ObjectCount):
        c = go.Object(i).Curve()
        if c:
            lines.append(Rhino.Geometry.Line(c.PointAtStart, c.PointAtEnd))
    return lines


def handle_mesh_input(option_name, hide=True):
    """Select Mesh objects from the Rhino document."""
    go = Rhino.Input.Custom.GetObject()
    go.SetCommandPrompt(f"Select {option_name}")
    go.GeometryFilter = Rhino.DocObjects.ObjectType.Mesh
    go.EnablePreSelect(True, True)
    go.SubObjectSelect = False
    go.DeselectAllBeforePostSelect = False
    go.GetMultiple(1, 0)
    meshes = []
    if go.CommandResult() == Rhino.Commands.Result.Success:
        for i in range(go.ObjectCount):
            obj = go.Object(i).Object()
            if hide:
                Rhino.RhinoDoc.ActiveDoc.Objects.Hide(obj.Id, True)
            if obj and obj.Geometry and isinstance(obj.Geometry, Rhino.Geometry.Mesh):
                meshes.append(obj.Geometry)
        Rhino.RhinoDoc.ActiveDoc.Views.Redraw()
    return meshes


def handle_surface_input(option_name, hide=True):
    """Select Surface objects from the Rhino document."""
    go = Rhino.Input.Custom.GetObject()
    go.SetCommandPrompt(f"Select {option_name}")
    go.GeometryFilter = Rhino.DocObjects.ObjectType.Surface
    go.EnablePreSelect(True, True)
    go.SubObjectSelect = False
    go.DeselectAllBeforePostSelect = False
    go.GetMultiple(1, 0)
    surfaces = []
    if go.CommandResult() == Rhino.Commands.Result.Success:
        for i in range(go.ObjectCount):
            obj = go.Object(i)
            srf = obj.Surface()
            if srf:
                surfaces.append(srf)
        Rhino.RhinoDoc.ActiveDoc.Views.Redraw()
    return surfaces


def handle_brep_input(option_name, hide=True):
    """Select Brep objects from the Rhino document."""
    go = Rhino.Input.Custom.GetObject()
    go.SetCommandPrompt(f"Select {option_name}")
    go.GeometryFilter = (
        Rhino.DocObjects.ObjectType.Surface | Rhino.DocObjects.ObjectType.PolysrfFilter
    )
    go.EnablePreSelect(True, True)
    go.SubObjectSelect = False
    go.DeselectAllBeforePostSelect = False
    go.GetMultiple(1, 0)
    breps = []
    if go.CommandResult() == Rhino.Commands.Result.Success:
        for i in range(go.ObjectCount):
            ref = go.Object(i)
            if hide:
                Rhino.RhinoDoc.ActiveDoc.Objects.Hide(ref, False)
            breps.append(ref.Brep())
    return breps


# ---------------------------------------------------------------------------
# Main declarative driver
# ---------------------------------------------------------------------------

def process_input(
    input_dict,
    callback=None,
    hide_input=True,
    run_when_input_changed=True,
    dataset_name=None,
):
    """Drive a Rhino command-line dialog from a declarative input dict.

    Parameters
    ----------
    input_dict : dict
        Mapping of ``option_name -> (default_value, type)``.
        Supported types: ``float``, ``int``, ``bool``, ``list[str]``,
        ``list[Rhino.Geometry.Polyline]``, ``list[Rhino.Geometry.Mesh]``,
        ``list[Rhino.Geometry.Brep]``, ``list[Rhino.Geometry.Line]``,
        ``list[Rhino.Geometry.TextDot]``, ``list[Rhino.Geometry.Point3d]``,
        ``list[float]``, ``list[int]``, ``Callable``.
    callback : callable, optional
        Called as ``callback(dict_values, dataset_name)`` whenever a value
        changes (and once at start).
    hide_input : bool
        Hide selected geometry after picking.
    run_when_input_changed : bool
        Re-invoke callback after every option change.
    dataset_name : str, optional
        Passed through to callback as second argument.
    """
    get_options = Rhino.Input.Custom.GetOption()

    dict_options = {}
    dict_values = {}

    for option_name, opt_def in input_dict.items():
        default_value, value_type = opt_def[0], opt_def[1]
        if value_type is float:
            dict_options[option_name] = Rhino.Input.Custom.OptionDouble(default_value)
            dict_values[option_name] = dict_options[option_name].CurrentValue
            get_options.AddOptionDouble(option_name, dict_options[option_name])
        elif value_type is int:
            dict_options[option_name] = Rhino.Input.Custom.OptionInteger(default_value)
            dict_values[option_name] = dict_options[option_name].CurrentValue
            get_options.AddOptionInteger(option_name, dict_options[option_name])
        elif value_type is bool:
            dict_options[option_name] = Rhino.Input.Custom.OptionToggle(
                default_value, "No", "Yes"
            )
            dict_values[option_name] = dict_options[option_name].CurrentValue
            get_options.AddOptionToggle(option_name, dict_options[option_name])
        elif get_origin(value_type) is list and get_args(value_type) == (str,):
            dict_options[option_name] = default_value[0]
            dict_values[option_name] = default_value[0]
            get_options.AddOptionList(option_name, default_value, 0)
        else:
            # All other list types (Polyline, Mesh, Brep, Line, float, int, …)
            dict_values[option_name] = []
            get_options.AddOption(option_name)

    # Fire callback once with initial/default values
    if callback and dict_values:
        for key, opt_def in input_dict.items():
            default_value = opt_def[0]
            if key not in dict_values or dict_values[key] == []:
                if isinstance(default_value, list) and default_value and isinstance(default_value[0], str):
                    dict_values[key] = default_value[0]
                else:
                    dict_values[key] = default_value
        callback(dict_values, dataset_name)

    get_options.SetCommandPrompt("Select input method and options.")

    done = False
    while not done:
        res = get_options.Get()

        if res == Rhino.Input.GetResult.Option:
            option_name = get_options.Option().EnglishName
            opt_def    = input_dict[option_name]
            input_type = opt_def[1]
            hint       = opt_def[2] if len(opt_def) > 2 else None

            if input_type is float or input_type is int or input_type is bool:
                dict_values[option_name] = dict_options[option_name].CurrentValue

            elif get_origin(input_type) is list and get_args(input_type) == (str,):
                dict_values[option_name] = opt_def[0][
                    get_options.Option().CurrentListOptionIndex
                ]

            elif get_origin(input_type) is list and get_args(input_type) == (float,):
                result = handle_numbers_input(option_name, hide_input)
                if result:
                    dict_values[option_name] = result
                    Rhino.RhinoApp.WriteLine(f"{option_name}: {result}")

            elif get_origin(input_type) is list and get_args(input_type) == (int,):
                result = handle_integers_input(option_name, hide_input)
                if result:
                    dict_values[option_name] = result
                    Rhino.RhinoApp.WriteLine(f"{option_name}: {result}")

            elif get_origin(input_type) is list and get_args(input_type) == (Rhino.Geometry.TextDot,):
                result = handle_textdots_input(option_name, hide_input)
                if result:
                    dict_values[option_name] = result
                    Rhino.RhinoApp.WriteLine(f"{option_name}: {len(result)} textdots")

            elif get_origin(input_type) is list and get_args(input_type) == (Rhino.Geometry.Point3d,):
                result = handle_points_input(option_name, hide_input)
                if result:
                    dict_values[option_name] = result
                    Rhino.RhinoApp.WriteLine(f"{option_name}: {len(result)} points")

            elif get_origin(input_type) is list and get_args(input_type) == (Rhino.Geometry.Line,):
                result = handle_lines_input(option_name, hide_input)
                if result:
                    dict_values[option_name] = result
                    Rhino.RhinoApp.WriteLine(f"{option_name}: {len(result)} lines")

            elif get_origin(input_type) is list and get_args(input_type) == (Rhino.Geometry.Polyline,):
                if hint:
                    Rhino.RhinoApp.WriteLine(hint)
                result = handle_polylines_input(option_name, hide_input)
                if result:
                    dict_values[option_name] = result
                    Rhino.RhinoApp.WriteLine(f"{option_name}: {len(result)} polylines selected")

            elif get_origin(input_type) is list and get_args(input_type) == (Rhino.Geometry.Mesh,):
                result = handle_mesh_input(option_name, hide_input)
                if result:
                    dict_values[option_name] = result
                    Rhino.RhinoApp.WriteLine(f"{option_name}: {len(result)} meshes")

            elif get_origin(input_type) is list and get_args(input_type) == (Rhino.Geometry.Brep,):
                result = handle_brep_input(option_name, hide_input)
                if result:
                    dict_values[option_name] = result
                    Rhino.RhinoApp.WriteLine(f"{option_name}: {len(result)} breps")

            elif get_origin(input_type) is list and get_args(input_type) == (Rhino.Geometry.Surface,):
                result = handle_surface_input(option_name, hide_input)
                if result:
                    dict_values[option_name] = result
                    Rhino.RhinoApp.WriteLine(f"{option_name}: {len(result)} surfaces")

            elif input_type is Callable:
                if dict_values[option_name]:
                    dict_values[option_name]()
                Rhino.RhinoApp.WriteLine(f"Function called: {option_name}")

            if run_when_input_changed and callback:
                callback(dict_values, dataset_name)

        elif res in (Rhino.Input.GetResult.Nothing, Rhino.Input.GetResult.Cancel):
            Rhino.RhinoApp.WriteLine("Exiting input dialog.")
            done = True

    if not run_when_input_changed and callback and dict_values:
        callback(dict_values, dataset_name)

    return Rhino.Commands.Result.Success
