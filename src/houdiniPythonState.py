import hou
import viewerstate.utils as su
import os

workpath = os.path.join(os.path.dirname(__file__))
download_folder = os.path.dirname(workpath) + "/downloads/"
hdri_folder = download_folder + "Hdris/"

class State(object):
    def __init__(self, state_name, scene_viewer):
        self.state_name = state_name
        self.scene_viewer = scene_viewer

    def onEnter(self,kwargs):
        self.scene_viewer.setPromptMessage( 
            'Drop a source file in the viewer', hou.promptMessageType.Prompt )

    def onDragTest( self, kwargs ):
        """ Accept text files only """
        if not hou.ui.hasDragSourceData('text/plain'):
            self.scene_viewer.setPromptMessage( 'Invalid drag drop source', 
                hou.promptMessageType.Error )
            return False

        # note: su.dragSourceFilepath returns the sanitized dragged file path
        su.log(su.dragSourceFilepath())

        return True

    def onDropGetOptions( self, kwargs ):
        """ Populate a drop option list with 3 items """
        kwargs['drop_options']['ids'] = ('mantraLgt', 'prmanLgt')
        kwargs['drop_options']['labels'] = ('Create Mantra Light', 'Create Prman Light')

    def onDropAccept( self, kwargs ):
        """ Process the event with the selected option. """
        hdri_name = hou.ui.getDragSourceData('text/plain')
        if kwargs['drop_selection'] == 'mantraLgt':
            for i in os.listdir(hdri_folder):
                j = i[:-7]
                if hdri_name == j:
                    node = hou.node("/obj/").createNode("envlight", "%s_HDRI"%(hdri_name))
                    node.parm("env_map").set(hdri_folder + i)
                    print(hdri_folder + i)

        if kwargs['drop_selection'] == 'prmanLgt':
            for i in os.listdir(hdri_folder):
                j = i[:-7]
                if hdri_name == j:
                    node = hou.node("/obj/").createNode("pxrdomelight::3.0", "%s_HDRI"%(hdri_name))
                    node.parm("lightColorMap").set(hdri_folder + i)

        su.log( kwargs['drop_selection'] )

        return True     
    

def createViewerStateTemplate():
    """ Mandatory entry point to create and return the viewer state 
        template to register. """

    state_typename = "Ak_Asset_Browser"
    state_label = "Ak_Asset_Browser"
    state_cat = hou.objNodeTypeCategory()

    template = hou.ViewerStateTemplate(state_typename, state_label, state_cat)
    template.bindFactory(State)
    template.bindIcon("MISC_python")

    return template