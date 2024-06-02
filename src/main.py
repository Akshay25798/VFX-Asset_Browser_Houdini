import hou
import viewerstate.utils as su
from PySide2 import QtNetwork
from PySide2.QtWidgets import QMenu, QPushButton
from PySide2.QtGui import QDrag
from PySide2 import QtWidgets, QtGui, QtCore
from PySide2.QtUiTools import QUiLoader
from PySide2.QtCore import Qt, QThread, Signal, QMimeData
import json, requests, os
from .flowLayout import FlowLayout

##
#path construntion
workpath = os.path.join(os.path.dirname(__file__))

font_path = workpath + "\\assets\\fonts\\"
font_id = QtGui.QFontDatabase.addApplicationFont(font_path + "Roboto-Medium.ttf")
# print(QtGui.QFontDatabase.applicationFontFamilies(font_id))

ui_file_path = workpath + "\\ui\\mainUI.ui"

download_folder = os.path.dirname(workpath) + "\\downloads\\"

thumbnail_folder = download_folder + "thumbnails\\"

json_folder = download_folder + "json\\"

##
#Poly Haven API - Url links
main_api =  "https://api.polyhaven.com/"
thumb_url = "https://cdn.polyhaven.com/asset_img/thumbs/"
asset_url = "https://api.polyhaven.com/files/"

#

def get_houdini_icon(icon, size=50):
    size = int(size)
    try:
        iconresult = hou.ui.createQtIcon(icon, size, size)
    except hou.OperationFailed:
        iconresult = hou.ui.createQtIcon("VIEW_visualization_scene", size, size)
    return iconresult


##--class starts

class GetLocalIcons(QThread):
    rowLoaded = Signal(list)  # Signal to emit when a row is loaded
    def __init__(self, parent, key, idx, total_assets):
        self.key = key
        self.total_assets = total_assets
        self.idx = idx
        # self.parent = parent
        super(GetLocalIcons, self).__init__(parent)

    def run(self):
        # print("Thread")
        size = 200
        key = self.key #str(self.parent().objectName())
        self.parent().setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        self.parent().setFixedSize(QtCore.QSize(size, size))
        self.parent().setIconSize(QtCore.QSize(size, size))
        self.parent().setText(key.replace("_", " ").title())
        self.parent().setStyleSheet("QToolButton{font-family: Roboto}")

        thumb_name = ("{0}.png".format(key))
        get_local_thumb = thumbnail_folder + thumb_name

        progress = int(self.idx) / int(self.total_assets) * 100
        self.rowLoaded.emit([self.parent(), get_local_thumb, progress])  # Emitting the loaded row
                

class IconDownloader(QtCore.QObject):
    def __init__(self, parent, req):
        self.req = req
        self.pixmap = QtGui.QPixmap()
        super(IconDownloader, self).__init__(parent)

    def start_fetch(self, net_mgr):
        self.fetch_task = net_mgr.get(self.req)
        self.fetch_task.finished.connect(self.resolve_fetch)

    def resolve_fetch(self):
        the_reply = self.fetch_task.readAll()
        self.set_widget_image(the_reply)

    def set_widget_image(self, img_binary):
        local_file_path = thumbnail_folder + self.parent().objectName() + ".png"
        local_thumbnail_file = open(local_file_path, "wb")
        local_thumbnail_file.write(img_binary)
        local_thumbnail_file.close()

        icon = QtGui.QIcon()
        icon.addPixmap(local_file_path)
        self.parent().setIcon(icon)
        # print(local_file_path)


class MainAssetBrowserUI(QtWidgets.QWidget): #main class
    def __init__(self):
        super(MainAssetBrowserUI, self).__init__()
        print("Asset_Brower_Started\n")
        self.setAcceptDrops(True)
        #managers 
        self.download_queue = QtNetwork.QNetworkAccessManager()
        self.threadpool = QtCore.QThreadPool.globalInstance()

        self.url = None
        self.file_size = None
        self.local_file = None
        self.data = None

        #load ui file
        self.loader = QUiLoader()
        self.ui = self.loader.load(ui_file_path)

        #get ui widgets from ui file
        self.contentArea = self.ui.ContantArea
        self.progress_bar = self.ui.progressBar
        self.status_bar = self.ui.statusBar
        self.icon_size_slider = self.ui.iconSize
        self.scrol_area_splitter = self.ui.scrollAreaSplitter
        self.tex_res = self.ui.texRes
        self.asset_format = self.ui.assetFormat
        self.asset_type = self.ui.assetTypes
        self.asset_catagories = self.ui.catagories


        #main layout and parameters
        self.main_layout = QtWidgets.QVBoxLayout()
        self.main_layout.setContentsMargins(0,0,0,0)
        self.main_layout.addWidget(self.ui)

        #setup for flowlayout
        self.widget = QtWidgets.QWidget()
        self.contentArea.setWidget(self.widget)
        self.assets_view = FlowLayout(self.widget)

        #set ui widgets property
        self.progress_bar.setProperty("visible", False)


        self.set_cagagories()
        # self.set_icons()
        self.asset_type.currentIndexChanged.connect(self.set_cagagories)
        self.asset_type.currentIndexChanged.connect(self.set_icons)
        
        self.asset_catagories.currentIndexChanged.connect(self.set_icons)
        # self.asset_catagories.currentIndexChanged.connect(self.check_asset_download_status)

        self.icon_size_slider.valueChanged.connect(self.set_icons_size)
        self.tex_res.currentIndexChanged.connect(self.check_asset_download_status)
        self.asset_format.currentIndexChanged.connect(self.check_asset_download_status)

        self.scrol_area_splitter.setStretchFactor(0,3)
        self.scrol_area_splitter.setStretchFactor(1,1)


        self.setLayout(self.main_layout)
        path = r"D:\PYTHON\VFX-Asset_Browser_Houdini\src\houdiniPythonState.py"
        hou.ui.registerViewerStateFile(path)


    ##--functions starts--
        

    def set_icons(self):

        if self.asset_type.currentIndex() == 0:
            json_file = json_folder + "hdris.json"
        elif self.asset_type.currentIndex() == 1:
            json_file = json_folder + "models.json"
        elif self.asset_type.currentIndex() == 2:
            json_file = json_folder + "textures.json"
        else:
            json_file = "hdris"

        self.clear_layout(self.assets_view) #clear the content area for new asset

        self.asset_in_catagory = [] #assets in current catagory
        current_catagory = self.asset_catagories.currentText()

        with open(json_file, "r") as read_content: #check if asset in current catagory
            data = json.load(read_content)
            for key in data.keys():
                if current_catagory in (data[key]["categories"]):
                    self.asset_in_catagory.append(key) #add asset to self.asset_in_catagory list
        

        for i, key in enumerate(self.asset_in_catagory): #get and set thumbnails for assets in catagory
            
            btn = DragButton() #QtWidgets.QToolButton()
            btn.setObjectName(key)
            self.assets_view.addWidget(btn)

            
            btn.clicked.connect(self.asset_clicked)
            total_assets = len(self.asset_in_catagory)
            self.status_bar.setText("total assets : %s"%(total_assets))       
            
            thumb_name = ("{0}.png".format(key))
            if not thumb_name in os.listdir(thumbnail_folder): #get icons form api
                # print("not in local")
                self.status_bar.setText("downloading %s thumbnail"%(thumb_name))
                url = thumb_url + key + ".png?height=" + str(500)
                req = QtNetwork.QNetworkRequest(QtCore.QUrl(url))
                download = IconDownloader(btn, req)
                download.start_fetch(self.download_queue)
                
            get_local_icon = GetLocalIcons(btn, key, i, total_assets)
            get_local_icon.rowLoaded.connect(self.set_local_icon)  # Connecting the signal to slot
            get_local_icon.start()
        self.check_asset_download_status()
        # print("Main thread compelete")

    #qt drops
    def dragEnterEvent(self, e):
        e.accept()

    def dropEvent(self, e):
        pos = e.pos()
        widget = e.source()
        print(e.mimeData().text())
        e.accept()

    def set_local_icon(self, btn):
        icon = QtGui.QIcon()
        icon.addPixmap(btn[1])
        btn[0].setIcon(icon)
        self.progress_fn(btn[2])


    def set_cagagories(self):
        if len(os.listdir(json_folder))==0: #check and download json files
            self.write_json_to_local()

        if self.asset_type.currentIndex() == 0:
            asset_type = "hdris"
        elif self.asset_type.currentIndex() == 1:
            asset_type = "models"
        elif self.asset_type.currentIndex() == 2:
            asset_type = "textures"
        else:
            asset_type = "hdris"

        catagory_json = json_folder + asset_type + "_catagories.json"
        self.asset_catagories.clear()
        with open(catagory_json, "r") as read_content: #read catagory form json
            d = json.load(read_content)
            catagory = d.keys()
            for i, key in enumerate(catagory):
                self.asset_catagories.insertItem(i, key)

        self.asset_catagories.setCurrentIndex(0) #set catagory option
        self.asset_catagories.setItemText(0, "None")

    def write_json_to_local(self):
        assets_types = ["hdris", "textures", "models"]
        for type in assets_types:
            self.status_bar.setText("downloading %s json files"%(type))
            assets_json = main_api + "assets?t=%s" % (type)
            categories_json =  main_api + "categories/%s" %(type)

            assets_json_data = requests.get(assets_json).json()
            categories_json_data = requests.get(categories_json).json()
            local_assets_json_file = json_folder + type + ".json"
            local_categories_json_file = json_folder + type + "_catagories.json"

            with open(local_assets_json_file, 'w', encoding='utf-8') as file: #json for assets full data
                json.dump(assets_json_data, file, ensure_ascii=False, indent=4)

            with open(local_categories_json_file, 'w', encoding='utf-8') as file:#json for catagories only 
                json.dump(categories_json_data, file, ensure_ascii=False, indent=4)

    def clear_layout(self, layout):
        while layout.count():
            child = layout.takeAt(0)
            self.status_bar.setText("clearing %s from contant area."%(child.widget().objectName()))
            # print("\nclearing: %s \n"%(child.widget().objectName()))
            if child.widget():
                child.widget().deleteLater()

    def check_asset_download_status(self):
        size = self.icon_size_slider.value()
        self.set_icons_size(size)


    def set_icons_size(self, size):
        icons = self.contentArea.findChildren(QtWidgets.QToolButton)
        font_size = int(5*(int(size)*0.01))
        border_size = 3
        icon_size_ratio = 0.8
        for icon in icons:
            icon.setFixedSize(QtCore.QSize(size, size))
            icon.setIconSize(QtCore.QSize(size * icon_size_ratio, size * icon_size_ratio))
            icon.setStyleSheet("QToolButton{font-size: %spt}"%(str(font_size)))

            local_asset_name = (("{0}_{1}.{2}".format(icon.objectName(), self.tex_res.currentText(), self.asset_format.currentText())))
            if local_asset_name in os.listdir(download_folder):
                icon.setStyleSheet("QToolButton{border: %spx solid #32CD32; font-size: %spt}"%(border_size, str(font_size)))
            else:
                icon.setStyleSheet("QToolButton{border: %spx solid #32CD32; font-size: %spt}"%(0, str(font_size)))
        self.status_bar.setText("icon size : " + str(size))
        

    def asset_clicked(self):
        if self.asset_type.currentIndex() == 0:
            asset_type ="hdri"
            folder_name = "Hdris\\"
        elif self.asset_type.currentIndex() == 1:
            asset_type ="fbx"
            folder_name = "Textures\\"
        elif self.asset_type.currentIndex() == 2:
            asset_type ="blend"
            folder_name = "Models\\"
        else:
            asset_type = "hdri"


        name = self.sender().objectName()
        tex_res = self.tex_res.currentText()
        asset_fomat = self.asset_format.currentText()
        path_to_check = "{0}{1}{2}_{3}.{4}".format(download_folder, folder_name, name, tex_res, asset_fomat)

        asset_json = requests.get(asset_url + name).json()
        print(asset_json['hdri'].keys())

        # if not os.path.exists(path_to_check): #download asset if not exists
        #     self.progress_bar.setValue(0)
        #     asset_json = requests.get(asset_url + name).json()
        #     self.url = asset_json[asset_type][tex_res][asset_fomat]["url"]
        #     self.file_size = asset_json["hdri"][tex_res][asset_fomat]["size"]

        #     local_file_name = download_folder + folder_name + os.path.basename(self.url)
        #     self.local_file = open(local_file_name, "wb")

        #     #worker for download assets
        #     worker = Worker(self.downloadImage)
        #     worker.signals.result.connect(self.print_output)
        #     worker.signals.finished.connect(self.thread_complete)
        #     worker.signals.progress.connect(self.progress_fn)

        #     #start the workder thread / execute
        #     self.threadpool.start(worker)
        


    def downloadImage(self, progress_callback):
        res = requests.get(self.url, stream=True)
        offset = 0    
        buffer = 512

        for chunk in res.iter_content(chunk_size=buffer):
            if not chunk:
                break
            self.local_file.seek(offset)
            self.local_file.write(chunk)
            offset = offset + len(chunk)

            progress = offset / int(self.file_size) * 100
            progress_callback.emit(progress)

        self.local_file.close()

    def progress_fn(self, n):
        self.progress_bar.setProperty("visible", True)
        self.progress_bar.setValue(0)
        self.progress_bar.setValue(n)
        self.progress_bar.setProperty("visible", False)
        # self.status_bar.setText("Loading : " + str(n) + "%")
        
        

    def print_output(self, s):
        # print("Result : ", s)
        pass

    def thread_complete(self):
        self.status_bar.setText("Done")
        self.progress_bar.setProperty("visible", False)
        self.check_asset_download_status()
        self.progress_bar.setProperty("visible", False)
        # print("Task Done!")

    def contextMenuEvent(self, event):
        menu = QMenu(self)
        Action1 = menu.addAction("Create Mantra Light")
        action = menu.exec_(self.mapToGlobal(event.pos()))

        if action == Action1:
            print(event.QPoint())
            # print(self.sender().objectName())


class DragButton(QtWidgets.QToolButton):

    def mouseMoveEvent(self, e):

        if e.buttons() == Qt.LeftButton:
            scene_viewer = hou.ui.paneTabOfType(hou.paneTabType.SceneViewer)
            scene_viewer.setCurrentState("Ak_Asset_Browser")
            drag = QDrag(self)
            mime = QMimeData()
            node = QtCore.QByteArray()
            node.setRawData("/obj/cam1", 16)
            mime.setData(hou.qt.mimeType.nodePath, node)
            mime.setText(str(node))

            drag.setMimeData(mime)

            pixmap = QtGui.QPixmap(self.size())
            self.render(pixmap)
            drag.setPixmap(pixmap)

            drag.setMimeData(mime)
            drag.exec_(Qt.MoveAction)



