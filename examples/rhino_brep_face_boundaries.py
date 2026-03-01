import Rhino
import rhinoscriptsyntax as rs
import scriptcontext as sc

def main():
    obj_id = rs.GetObject("Select brep", rs.filter.polysurface | rs.filter.surface)
    if obj_id is None:
        return

    obj = sc.doc.Objects.Find(obj_id)
    brep = obj.Geometry
    if not isinstance(brep, Rhino.Geometry.Brep):
        return

    tol = sc.doc.ModelAbsoluteTolerance
    added = 0

    for fi, face in enumerate(brep.Faces):
        for loop in face.Loops:
            crv = loop.To3dCurve()
            if crv is None or not crv.IsValid:
                continue
            attr = Rhino.DocObjects.ObjectAttributes()
            attr.Name = "face{}_loop{}".format(fi, loop.LoopIndex)
            attr.ObjectColor = (
                System.Drawing.Color.Red
                if loop.LoopType == Rhino.Geometry.BrepLoopType.Outer
                else System.Drawing.Color.Blue
            )
            attr.ColorSource = Rhino.DocObjects.ObjectColorSource.ColorFromObject
            sc.doc.Objects.AddCurve(crv, attr)
            added += 1

    sc.doc.Views.Redraw()
    print("{} boundary curves added ({} faces)".format(added, brep.Faces.Count))

import System
main()
