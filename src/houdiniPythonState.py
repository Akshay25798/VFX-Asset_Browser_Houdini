import hou
import viewerstate.utils as su
import os
import nodegraphutils as utils

workpath = os.path.join(os.path.dirname(__file__))
download_folder = os.path.dirname(workpath) + "/downloads/"
hdri_folder = download_folder + "Hdris/"
thumbnail_folder = download_folder + "thumbnails/"

class State(object):
    def __init__(self, state_name, scene_viewer):
        self.state_name = state_name
        self.scene_viewer = scene_viewer
        
    def onEnter(self,kwargs):
        self.scene_viewer.setPromptMessage( 
            "Drop a source file in the viewer", hou.promptMessageType.Prompt )

    def onDragTest( self, kwargs ):
        """ Accept text files only """
        if not hou.ui.hasDragSourceData("text/plain"):
            self.scene_viewer.setPromptMessage( "Invalid drag drop source", 
                hou.promptMessageType.Error )
            return False

        # note: su.dragSourceFilepath returns the sanitized dragged file path
        su.log(su.dragSourceFilepath())

        return True

    def onDropGetOptions( self, kwargs ):
        """ Populate a drop option list with 3 items """
        kwargs["drop_options"]["ids"] = ("mantraLgt", "prmanLgt")
        kwargs["drop_options"]["labels"] = ("Create Mantra Light", "Create Prman Light")

    def onDropAccept( self, kwargs ):
        """ Process the event with the selected option. """
        selection_name = hou.ui.getDragSourceData("text/plain")
        self.create_hdri_node(kwargs["drop_selection"], selection_name)
        su.log( kwargs["drop_selection"] )
        return True     

    def create_hdri_node(self, selection, selection_name):
        hdri_name = selection_name #hou.ui.getDragSourceData("text/plain")
        node_dict = {"mantraLgt":["envlight", "env_map"], "prman":["pxrdomelight::3.0", "lightColorMap"]}

        if selection in list(node_dict.keys()):
            for i in os.listdir(hdri_folder):
                j = i[:-7]
                if hdri_name == j:
                    node = hou.node("/obj/").createNode(node_dict[selection][0], "%s_HDRI"%(hdri_name))
                    node.parm(node_dict[selection][1]).set(hdri_folder + i)
                    node.moveToGoodPosition()
                    node.setCurrent(True, clear_all_selected=True)
                    self.add_bg_image(node, hdri_name)

            editor = hou.ui.paneTabOfType(hou.paneTabType.NetworkEditor)
            editor.homeToSelection()
    
    def add_bg_image(self, node, thumb_name):
        thumb_path = thumbnail_folder + thumb_name + ".png"
        editor = hou.ui.paneTabOfType(hou.paneTabType.NetworkEditor)
        image = hou.NetworkImage()
        image.setPath(thumb_path)
        image.setRect(hou.BoundingRect(-2, 0.25, 5, 2.5))
        image.setRelativeToPath(node.path())
        bg_image = editor.backgroundImages()
        bg_image = bg_image + (image,)
        editor.setBackgroundImages(bg_image)
        utils.saveBackgroundImages(editor.pwd(), bg_image)

        hou_parm_template_group = hou.ParmTemplateGroup()
        hou_parm_template = hou.LabelParmTemplate("bg_image_parm", "Label", column_labels=([thumb_path]))
        hou_parm_template.hideLabel(True)
        hou_parm_template_group.append(hou_parm_template)
        node.setParmTemplateGroup(hou_parm_template_group)

        sel = hou.selectedNodes()
        selected_node = ""
        if sel:
            selected_node = sel[-1]
        selected_node.addEventCallback((hou.nodeEventType.BeingDeleted,), self.remove_bg_image)

    def remove_bg_image(self, **kwargs):
        deletingNode = [x[1] for x in kwargs.items()][0]
        image = deletingNode.parm("bg_image_parm").eval()
        editor = hou.ui.paneTabOfType(hou.paneTabType.NetworkEditor)
        bg_image = editor.backgroundImages()
        bg_image = tuple(x for x in bg_image if hou.expandString(x.path()) != hou.expandString(image))
        editor.setBackgroundImages(bg_image)
        utils.saveBackgroundImages(editor.pwd(), bg_image)

        
def createViewerStateTemplate():
    """ Mandatory entry point to create and return the viewer state 
        template to register. """

    state_typename = "Ak_Asset_Browser"
    state_label = state_typename
    state_cat = hou.objNodeTypeCategory()

    template = hou.ViewerStateTemplate(state_typename, state_label, state_cat)
    template.bindFactory(State)
    template.bindIcon("MISC_python")

    return template