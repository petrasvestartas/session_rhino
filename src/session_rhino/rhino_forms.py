"""Eto.Forms dialogs for editing named values and booleans.

Adapted from wood_rui/forms.py (petrasvestartas/wood_rui).

Classes
-------
NamedValuesForm
    GridView dialog with editable text values.
BooleanForm
    GridView dialog with editable checkbox values.
"""

import ast

import Eto.Drawing  # type: ignore
import Eto.Forms  # type: ignore
import Rhino  # type: ignore
import Rhino.UI  # type: ignore
import System  # type: ignore


class NamedValuesForm(Eto.Forms.Dialog[bool]):
    """Eto dialog for displaying and editing named values.

    Parameters
    ----------
    names : list[str]
        Names column.
    values : list
        Values column (converted to string for display; parsed back on OK).
    title : str, optional
        Window title.
    width : int, optional
        Window width in pixels.
    height : int, optional
        Window height in pixels.

    Attributes
    ----------
    attributes : list[tuple[str, any]]
        Name/value pairs after the user clicks OK.

    Returns
    -------
    bool
        ``True`` when user clicks OK, ``False`` on Cancel.
    """

    def __init__(self, names, values, title="Named Values", width=600, height=800):
        super().__init__()

        self.attributes = list(zip(names, values))
        self.names = names
        self.values = [str(v) for v in values]

        self.Title = title
        self.Padding = Eto.Drawing.Padding(0)
        self.Resizable = True
        self.MinimumSize = Eto.Drawing.Size(width // 2, height // 2)
        self.ClientSize = Eto.Drawing.Size(width, height)

        self.table = table = Eto.Forms.GridView()
        table.ShowHeader = True

        col_name = Eto.Forms.GridColumn()
        col_name.HeaderText = "Name"
        col_name.Editable = False
        col_name.DataCell = Eto.Forms.TextBoxCell(0)
        table.Columns.Add(col_name)

        col_val = Eto.Forms.GridColumn()
        col_val.HeaderText = "Value"
        col_val.Editable = True
        col_val.DataCell = Eto.Forms.TextBoxCell(1)
        table.Columns.Add(col_val)

        collection = []
        for name, value in zip(self.names, self.values):
            item = Eto.Forms.GridItem()
            item.Values = (name, value)
            collection.append(item)
        table.DataStore = collection

        layout = Eto.Forms.DynamicLayout()
        layout.BeginVertical(Eto.Drawing.Padding(0), Eto.Drawing.Size(0, 0), True, True)
        layout.AddRow(table)
        layout.EndVertical()
        layout.BeginVertical(Eto.Drawing.Padding(12, 18, 12, 24), Eto.Drawing.Size(6, 0), False, False)
        layout.AddRow(None, self._ok_button(), self._cancel_button())
        layout.EndVertical()
        self.Content = layout

    def _ok_button(self):
        self.DefaultButton = Eto.Forms.Button()
        self.DefaultButton.Text = "OK"
        self.DefaultButton.Click += self._on_ok
        return self.DefaultButton

    def _cancel_button(self):
        self.AbortButton = Eto.Forms.Button()
        self.AbortButton.Text = "Cancel"
        self.AbortButton.Click += self._on_cancel
        return self.AbortButton

    @staticmethod
    def _is_path(value):
        return isinstance(value, str) and ("\\" in value or "/" in value)

    def _on_ok(self, sender, event):
        try:
            self.attributes = []
            for row in self.table.DataStore:
                name = row.GetValue(0)
                value = row.GetValue(1)
                if value not in ("-", "", " "):
                    try:
                        if not self._is_path(value):
                            value = ast.literal_eval(value)
                    except (ValueError, SyntaxError):
                        pass
                self.attributes.append((name, value))
        except Exception as e:
            print(e)
            self.Close(False)
            return
        self.Close(True)

    def _on_cancel(self, sender, event):
        self.Close(False)

    def show(self):
        """Show the dialog modally. Returns True if user clicked OK."""
        return self.ShowModal(Rhino.UI.RhinoEtoApp.MainWindow)


class BooleanForm(Eto.Forms.Dialog[bool]):
    """Eto dialog for displaying and editing boolean values via checkboxes.

    Parameters
    ----------
    names : list[str]
        Names column.
    values : list[bool]
        Boolean values column.
    title : str, optional
        Window title.
    width : int, optional
        Window width in pixels.
    height : int, optional
        Window height in pixels.

    Attributes
    ----------
    attributes : list[tuple[str, bool]]
        Name/bool pairs after the user clicks OK.

    Returns
    -------
    bool
        ``True`` when user clicks OK, ``False`` on Cancel.
    """

    def __init__(self, names, values, title="Boolean Form", width=600, height=800):
        super().__init__()

        self.attributes = list(zip(names, values))
        self.names = names
        self.values = values

        self.Title = title
        self.Padding = Eto.Drawing.Padding(0)
        self.Resizable = True
        self.MinimumSize = Eto.Drawing.Size(width // 2, height // 2)
        self.ClientSize = Eto.Drawing.Size(width, height)

        self.table = table = Eto.Forms.GridView()
        table.ShowHeader = True

        col_name = Eto.Forms.GridColumn()
        col_name.HeaderText = "Name"
        col_name.Editable = False
        col_name.DataCell = Eto.Forms.TextBoxCell(0)
        table.Columns.Add(col_name)

        col_val = Eto.Forms.GridColumn()
        col_val.HeaderText = "Value"
        col_val.Editable = True
        col_val.DataCell = Eto.Forms.CheckBoxCell(1)
        table.Columns.Add(col_val)

        collection = []
        for name, value in zip(self.names, self.values):
            item = Eto.Forms.GridItem()
            item.Values = (name, value)
            collection.append(item)
        table.DataStore = collection

        layout = Eto.Forms.DynamicLayout()
        layout.BeginVertical(Eto.Drawing.Padding(0), Eto.Drawing.Size(0, 0), True, True)
        layout.AddRow(table)
        layout.EndVertical()
        layout.BeginVertical(Eto.Drawing.Padding(12, 18, 12, 24), Eto.Drawing.Size(6, 0), False, False)
        layout.AddRow(None, self._ok_button(), self._cancel_button())
        layout.EndVertical()
        self.Content = layout

    def _ok_button(self):
        self.DefaultButton = Eto.Forms.Button()
        self.DefaultButton.Text = "OK"
        self.DefaultButton.Click += self._on_ok
        return self.DefaultButton

    def _cancel_button(self):
        self.AbortButton = Eto.Forms.Button()
        self.AbortButton.Text = "Cancel"
        self.AbortButton.Click += self._on_cancel
        return self.AbortButton

    def _on_ok(self, sender, event):
        try:
            self.attributes = []
            for row in self.table.DataStore:
                name = row.GetValue(0)
                value = row.GetValue(1)
                self.attributes.append((name, bool(value)))
        except Exception as e:
            print(e)
            self.Close(False)
            return
        self.Close(True)

    def _on_cancel(self, sender, event):
        self.Close(False)

    def show(self):
        """Show the dialog modally. Returns True if user clicked OK."""
        return self.ShowModal(Rhino.UI.RhinoEtoApp.MainWindow)
