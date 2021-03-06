#Copyright (c) 2018 Ultimaker B.V.
#Cura is released under the terms of the LGPLv3 or higher.

from Charon.VirtualFile import VirtualFile #To open UFP files.
from Charon.OpenMode import OpenMode #To indicate that we want to write to UFP files.
from io import StringIO #For converting g-code to bytes.

from UM.Application import Application
from UM.Logger import Logger
from UM.Mesh.MeshWriter import MeshWriter #The writer we need to implement.
from UM.PluginRegistry import PluginRegistry #To get the g-code writer.
from PyQt5.QtCore import QBuffer

from cura.Snapshot import Snapshot


class UFPWriter(MeshWriter):
    def __init__(self):
        super().__init__()
        self._snapshot = None
        Application.getInstance().getOutputDeviceManager().writeStarted.connect(self._createSnapshot)

    def _createSnapshot(self, *args):
        # must be called from the main thread because of OpenGL
        Logger.log("d", "Creating thumbnail image...")
        self._snapshot = Snapshot.snapshot(width = 300, height = 300)

    def write(self, stream, nodes, mode = MeshWriter.OutputMode.BinaryMode):
        archive = VirtualFile()
        archive.openStream(stream, "application/x-ufp", OpenMode.WriteOnly)

        #Store the g-code from the scene.
        archive.addContentType(extension = "gcode", mime_type = "text/x-gcode")
        gcode_textio = StringIO() #We have to convert the g-code into bytes.
        PluginRegistry.getInstance().getPluginObject("GCodeWriter").write(gcode_textio, None)
        gcode = archive.getStream("/3D/model.gcode")
        gcode.write(gcode_textio.getvalue().encode("UTF-8"))
        archive.addRelation(virtual_path = "/3D/model.gcode", relation_type = "http://schemas.ultimaker.org/package/2018/relationships/gcode")

        #Store the thumbnail.
        if self._snapshot:
            archive.addContentType(extension = "png", mime_type = "image/png")
            thumbnail = archive.getStream("/Metadata/thumbnail.png")

            thumbnail_buffer = QBuffer()
            thumbnail_buffer.open(QBuffer.ReadWrite)
            thumbnail_image = self._snapshot
            thumbnail_image.save(thumbnail_buffer, "PNG")

            thumbnail.write(thumbnail_buffer.data())
            archive.addRelation(virtual_path = "/Metadata/thumbnail.png", relation_type = "http://schemas.openxmlformats.org/package/2006/relationships/metadata/thumbnail", origin = "/3D/model.gcode")
        else:
            Logger.log("d", "Thumbnail not created, cannot save it")

        archive.close()
        return True
