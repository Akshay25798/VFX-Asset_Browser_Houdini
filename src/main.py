import hou
import nodegraphutils as utils
from PySide2 import QtNetwork
from PySide2.QtGui import QDrag
from PySide2 import QtWidgets, QtGui, QtCore
from PySide2.QtUiTools import QUiLoader
from PySide2.QtCore import Qt, QThread, Signal, QMimeData
from PySide2.QtWidgets import QToolButton, QAction, QMenu
import json, requests, os
from .flowLayout import FlowLayout
from .worker import Worker
from .houdiniPythonState import State

##
#path construntion
workpath = os.path.join(os.path.dirname(__file__))

font_path = workpath + "/assets/fonts/"
font_id = QtGui.QFontDatabase.addApplicationFont(font_path + "Roboto-Medium.ttf")
# print(QtGui.QFontDatabase.applicationFontFamilies(font_id))

ui_file_path = workpath + "/ui/mainUI.ui"

download_folder = os.path.dirname(workpath) + "/downloads/"

hdri_folder = download_folder + "Hdris/"

model_folder = download_folder + "Models/"

texture_folder = download_folder + "Textures/"

thumbnail_folder = download_folder + "thumbnails/"

json_folder = download_folder + "json/"

pythonState_path = workpath + "/houdiniPythonState.py"

##
#Poly Haven API - Url links
main_api =  "https://api.polyhaven.com/"
thumb_url = "https://cdn.polyhaven.com/asset_img/thumbs/"
asset_url = "https://api.polyhaven.com/files/"

##--class starts

class GetLocalIcons(QThread):
    rowLoaded = Signal(int)  # Signal to emit when a row is loaded
    def __init__(self, parent, key, idx, total_assets):
        self.key = key
        self.total_assets = total_assets
        self.idx = idx + 1
        self.icon = QtGui.QIcon()
        super(GetLocalIcons, self).__init__(parent)

    def run(self):
        size = 200
        key = self.key #str(self.parent().objectName())
        self.parent().setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        self.parent().setFixedSize(QtCore.QSize(size, size))
        self.parent().setIconSize(QtCore.QSize(size, size))
        self.parent().setText(key.replace("_", " ").title())
        self.parent().setStyleSheet("QToolButton{font-family: Roboto}")

        thumb_name = ("{0}.png".format(key))
        get_local_thumb = thumbnail_folder + thumb_name
        self.icon.addPixmap(get_local_thumb)
        self.parent().setIcon(self.icon)
        progress = int(float(self.idx) / float(self.total_assets) * 100)
        self.rowLoaded.emit(progress)  # Emitting the loaded row
                
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

class MainAssetBrowserUI(QtWidgets.QWidget, State): #main class
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
        self.tex_res = self.ui.texRes
        self.asset_format = self.ui.assetFormat
        self.asset_type = self.ui.assetTypes
        self.asset_categories = self.ui.catagories
        self.offline = self.ui.checkBox
        self.total_assets_count = self.ui.totalAssets
        self.search_box = self.ui.search

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

        self.set_categories()
        self.set_icons()
        self.asset_type.currentIndexChanged.connect(self.set_categories)
        self.asset_type.currentIndexChanged.connect(self.set_icons)
        self.asset_categories.currentIndexChanged.connect(self.set_icons)
        self.icon_size_slider.valueChanged.connect(self.set_icons_size)
        self.tex_res.currentIndexChanged.connect(self.check_asset_download_status)
        self.asset_format.currentIndexChanged.connect(self.check_asset_download_status)
        self.search_box.textChanged.connect(self.search)
        self.offline.toggled.connect(self.set_icons)

        self.setLayout(self.main_layout)
        hou.ui.registerViewerStateFile(pythonState_path)
        self.show_flash_msg("Drag HDRI on the viewport or use right click.", 10)

    ##--functions starts--      
    def set_icons(self):
        self.clear_layout(self.assets_view) #clear the content area for new asset
        if self.asset_type.currentIndex() == 0:
            json_file = json_folder + "hdris.json"
            self.get_icons(json_file, hdri_folder)
        elif self.asset_type.currentIndex() == 1:
            json_file = json_folder + "models.json"
            self.get_icons(json_file, model_folder)
        elif self.asset_type.currentIndex() == 2:
            json_file = json_folder + "textures.json"
            self.get_icons(json_file, texture_folder)
        elif self.asset_type.currentIndex() == 3:
            label = QtWidgets.QLabel("Coming soon !!!")
            label.setStyleSheet("QLabel{font-size: 15pt; font-family: Roboto}")
            self.assets_view.addWidget(label)
        elif self.asset_type.currentIndex() == 4:
            label = QtWidgets.QLabel("Coming soon !!!")
            label.setStyleSheet("QLabel{font-size: 15pt; font-family: Roboto}")
            self.assets_view.addWidget(label)
        else:
            label = QtWidgets.QLabel("Working on it !!!")
            label.setStyleSheet("QLabel{font-size: 15pt; font-family: Roboto}")
            self.assets_view.addWidget(label)
        
    def get_icons(self, json_file, type): #helper defination for set_icons
        self.asset_in_catagory = [] #assets in current catagory
        current_catagory = self.asset_categories.currentText()

        with open(json_file, "r") as read_content: #check if asset in current catagory
            data = json.load(read_content)
            for key in data.keys():
                if current_catagory in (data[key]["categories"]):
                    self.asset_in_catagory.append(key) #add asset to self.asset_in_catagory list

        total_assets = ""
        if self.asset_categories.currentIndex() == 0: #if all selected in catagory
            available_offline = []
            for i in os.listdir(type):
                if i.endswith(".tex") == False:
                    j = i[:-7]
                    available_offline.append(j)
            total_assets = len(available_offline)
            self.total_assets_count.setText("Total Assets : %s" %(total_assets))

            for i, key in enumerate(available_offline): #get and set thumbnails for assets in catagory
                btn = DragButton() #QtWidgets.QToolButton()
                btn.setObjectName(key)
                btn.mouseHover.connect(self.hover)
                self.assets_view.addWidget(btn)
                btn.clicked.connect(self.asset_clicked)  
                thumb_name = ("{0}.png".format(key))

                get_local_icon = GetLocalIcons(btn, key, i, total_assets)
                QtCore.QCoreApplication.processEvents() #to keep app responsive
                get_local_icon.rowLoaded.connect(self.progress_fn)  # Connecting the signal to slot
                get_local_icon.start()
        else:
            if self.offline.isChecked() == True: #if available checked
                available_offline = []
                for i in os.listdir(type):
                    j = i[:-7]
                    if j in self.asset_in_catagory:
                        available_offline.append(j)
                total_assets = len(available_offline)
                self.total_assets_count.setText("Total Assets : %s" %(total_assets))

                for i, key in enumerate(available_offline): #get and set thumbnails for assets in catagory
                    btn = DragButton() #QtWidgets.QToolButton()
                    btn.setObjectName(key)
                    btn.mouseHover.connect(self.hover)
                    self.assets_view.addWidget(btn)
                    btn.clicked.connect(self.asset_clicked)
                    thumb_name = ("{0}.png".format(key))

                    get_local_icon = GetLocalIcons(btn, key, i, total_assets)
                    QtCore.QCoreApplication.processEvents() #to keep app responsive
                    get_local_icon.rowLoaded.connect(self.progress_fn)  # Connecting the signal to slot
                    get_local_icon.start()
                

            else: #if available not checked
                for i, key in enumerate(self.asset_in_catagory): #get and set thumbnails for assets in catagory
                    btn = DragButton() #QtWidgets.QToolButton()
                    btn.setObjectName(key)
                    btn.mouseHover.connect(self.hover)
                    self.assets_view.addWidget(btn)
                    btn.clicked.connect(self.asset_clicked)
                    thumb_name = ("{0}.png".format(key))
                    total_assets = len(self.asset_in_catagory)
                    self.total_assets_count.setText("Total Assets : %s" %(total_assets))

                    if not thumb_name in os.listdir(thumbnail_folder): #get icons form api
                        # print("not in local")
                        self.status_bar.setText("downloading %s thumbnail"%(thumb_name))
                        url = thumb_url + key + ".png?height=" + str(500)
                        req = QtNetwork.QNetworkRequest(QtCore.QUrl(url))
                        download = IconDownloader(btn, req)
                        download.start_fetch(self.download_queue)
                    get_local_icon = GetLocalIcons(btn, key, i, total_assets)
                    QtCore.QCoreApplication.processEvents() #to keep app responsive
                    get_local_icon.rowLoaded.connect(self.progress_fn)  # Connecting the signal to slot
                    get_local_icon.start()


        self.check_asset_download_status()
        self.status_bar.setText("Total assets : %s" %(total_assets))

    def search(self, text):
        icons = self.contentArea.findChildren(QtWidgets.QToolButton)
        for icon in icons:
            icon_name = icon.objectName()
            if text.lower() in icon_name.lower():
                icon.show()
            else:
                icon.hide()

    def hover(self, e):
        if e == True:
            size = self.icon_size_slider.value()
            scale = 1.25
            font_size = int(2.5*(int(size * scale)*0.01))
            border_size = 3 * scale
            icon_size_ratio = 0.8
            self.setToolTip(self.sender().objectName())
            self.status_bar.setText(self.sender().objectName())
            self.sender().setFixedSize(QtCore.QSize(size + scale, size + scale))
            self.sender().setIconSize(QtCore.QSize((size * scale) * icon_size_ratio, (size * scale) * icon_size_ratio))
            self.sender().setStyleSheet("QToolButton{border: %spx solid #F4C430; font-size: %spt; font-family: Roboto}"%(border_size, str(font_size))) 
        else:
            self.check_asset_download_status()
            
    #qt drops
    def dragEnterEvent(self, e):
        #network editor drop
        self.asset_name = e.mimeData().text()
        hou.ui.addEventLoopCallback(self.drop_on_networkeditor)
        e.accept()

    def dropEvent(self, e):
        pos = e.pos()
        widget = e.source()
        e.accept()

    def drop_on_networkeditor(self):
        tab_under_cursor = hou.ui.paneTabUnderCursor()
        if tab_under_cursor.type().name() == "NetworkEditor":
            hou.ui.removeEventLoopCallback(self.drop_on_networkeditor)
            self.context_menu = QMenu(self)
            #create right click menu
            self.action1 = QAction("Create Mantra Light", self)
            self.action2 = QAction("Create Prman Light", self)

            self.context_menu.addAction(self.action1)
            self.context_menu.addAction(self.action2)

            #connect action to functions
            self.action1.triggered.connect(self.action1_triggered)
            self.action2.triggered.connect(self.action2_triggered)
            self.context_menu.exec_(QtGui.QCursor.pos())

    def action1_triggered(self):
        selection_name = self.asset_name
        selection = "mantraLgt"
        State.create_hdri_node(self, selection, selection_name)
        print(selection_name)

    def action2_triggered(self):
        selection_name = self.asset_name
        selection = "prmanLgt"
        State.create_hdri_node(self, selection, selection_name)

    def set_categories(self):
        if len(os.listdir(json_folder))==0: #check and download json files
            self.write_json_to_local()

        if self.asset_type.currentIndex() == 0:
            asset_type = "hdris"
            self.get_categories(asset_type)
        elif self.asset_type.currentIndex() == 1:
            asset_type = "models"
            self.get_categories(asset_type)
        elif self.asset_type.currentIndex() == 2:
            asset_type = "textures"
            self.get_categories(asset_type)
        else:
            self.asset_categories.clear()

    def get_categories(self, asset_type): #helder defination
        catagory_json = json_folder + asset_type + "_catagories.json"
        self.asset_categories.clear()
        with open(catagory_json, "r") as read_content: #read catagory form json
            d = json.load(read_content)
            catagory = d.keys()
            for i, key in enumerate(catagory):
                self.asset_categories.insertItem(i, key)
        self.asset_categories.setItemText(0, "All Available")
        self.asset_categories.setCurrentIndex(0) #set catagory option

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
        self.set_icons_size(size, )

    def set_icons_size(self, size):
        if self.asset_type.currentIndex() == 0:
            self.get_icons_size(size, hdri_folder)
        elif self.asset_type.currentIndex() == 1:
            self.get_icons_size(size, model_folder)
        elif self.asset_type.currentIndex() == 2:
            self.get_icons_size(size, texture_folder)
        elif self.asset_type.currentIndex() == 3:
            label = QtWidgets.QLabel("Coming soon !!!")
            label.setStyleSheet("QLabel{font-size: 15pt; font-family: Roboto}")
            self.assets_view.addWidget(label)
        elif self.asset_type.currentIndex() == 4:
            label = QtWidgets.QLabel("Coming soon !!!")
            label.setStyleSheet("QLabel{font-size: 15pt; font-family: Roboto}")
            self.assets_view.addWidget(label)
        else:
            label = QtWidgets.QLabel("Working on it !!!")
            label.setStyleSheet("QLabel{font-size: 15pt; font-family: Roboto}")
            self.assets_view.addWidget(label)

    def get_icons_size(self, size, type):
        icons = self.contentArea.findChildren(QtWidgets.QToolButton)
        font_size = int(2.5*(int(size)*0.01))
        border_size = 3
        icon_size_ratio = 0.8
        for icon in icons:
            icon.setFixedSize(QtCore.QSize(size, size))
            icon.setIconSize(QtCore.QSize(size * icon_size_ratio, size * icon_size_ratio))
            icon.setStyleSheet("QToolButton{font-size: %spt}"%(str(font_size)))

            local_asset_name = (("{0}_{1}.{2}".format(icon.objectName(), self.tex_res.currentText(), self.asset_format.currentText())))
            if local_asset_name in os.listdir(type):
                icon.setStyleSheet("QToolButton{border: %spx solid #32CD32; font-size: %spt; font-family: Roboto}"%(border_size, str(font_size)))
            else:
                icon.setStyleSheet("QToolButton{border: %spx solid #32CD32; font-size: %spt; font-family: Roboto}"%(0, str(font_size)))
        self.status_bar.setText("icon size : " + str(size))
        
    def asset_clicked(self):
        if self.asset_type.currentIndex() == 0:
            asset_type ="hdri"
            folder_name = "Hdris/"
        elif self.asset_type.currentIndex() == 1:
            asset_type ="fbx"
            folder_name = "Textures/"
        elif self.asset_type.currentIndex() == 2:
            asset_type ="blend"
            folder_name = "Models/"
        else:
            asset_type = "hdri"

        node = hou.selectedNodes()
        name = self.sender().objectName()
        tex_res = self.tex_res.currentText()
        asset_fomat = self.asset_format.currentText()
        path_to_check = "{0}{1}{2}_{3}.{4}".format(download_folder, folder_name, name, tex_res, asset_fomat)

        asset_json = requests.get(asset_url + name).json()
    
        if len(node) > 0: #overwrite the selected node
            light_type = node[0].type().name()
            msgBox = QtWidgets.QMessageBox.question(self, "Conformation", "Overwrite the selected node!!!")
            if msgBox == QtWidgets.QMessageBox.Yes:
                if light_type == "envlight":
                    for i in os.listdir(hdri_folder):
                        j = i[:-7]
                        if name == j:
                            node[0].parm("env_map").set(hdri_folder + i)
                if light_type == "pxrdomelight::3.0":
                    for i in os.listdir(hdri_folder):
                        j = i[:-7]
                        if name == j:
                            node[0].parm("lightColorMap").set(hdri_folder + i)
                            node[0].parm("bg_image_path").set(image_path)

                #change bg image
                image_to_remove = node[0].parm("bg_image_parm").eval()
                image_path = thumbnail_folder + name + ".png"
                image = hou.NetworkImage()
                image.setPath(image_path)
                image.setRect(hou.BoundingRect(-2, 0.25, 5, 2.5))
                image.setRelativeToPath(node[0].path())
                

                editor = hou.ui.paneTabOfType(hou.paneTabType.NetworkEditor)
                bg_image = editor.backgroundImages()
                bg_image = tuple(x for x in bg_image if hou.expandString(x.path()) != hou.expandString(image_to_remove))
                bg_image = bg_image + (image, )

                editor.setBackgroundImages(bg_image)
                utils.saveBackgroundImages(editor.pwd(), bg_image)
        else:
            self.show_flash_msg("Select ligh node to overwrite or just drag on the viewport.", 10)
                

        if not os.path.exists(path_to_check): #download asset if not exists
            self.progress_bar.setValue(0)
            asset_json = requests.get(asset_url + name).json()
            self.url = asset_json[asset_type][tex_res][asset_fomat]["url"]
            self.file_size = asset_json["hdri"][tex_res][asset_fomat]["size"]

            local_file_name = download_folder + folder_name + os.path.basename(self.url)
            self.local_file = open(local_file_name, "wb")

            #worker for download assets
            worker = Worker(self.downloadImage)
            worker.signals.result.connect(self.print_output)
            worker.signals.finished.connect(self.thread_complete)
            worker.signals.progress.connect(self.progress_fn)

            #start the workder thread / execute
            self.threadpool.start(worker)

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
        self.status_bar.setText("Loading : " + str(n) + "%")
        if n == 100:
            self.progress_bar.setProperty("visible", False)
            self.status_bar.setText("Loading Done")
        
    def print_output(self, s):
        # print("Result : ", s)
        pass

    def thread_complete(self):
        self.status_bar.setText("Done")
        self.progress_bar.setValue(0)
        self.progress_bar.setProperty("visible", False)
        self.check_asset_download_status()

    def show_flash_msg(self, msg, time):
        editor = hou.ui.paneTabOfType(hou.paneTabType.NetworkEditor)
        img = "hicon:/SVGIcons.index?SHELF_atmosphere.svg"
        editor.flashMessage(image=img, message=msg, duration=time)

class DragButton(QToolButton, State):
    mouseHover = Signal(bool)
    def __init__(self): #hover event
        super(DragButton, self).__init__()
        self.setMouseTracking(True)

        self.context_menu = QMenu(self)
        #create right click menu
        self.action1 = QAction("Create Mantra Light", self)
        self.action2 = QAction("Create Prman Light", self)
        self.action3 = QAction("Open HDRI's Folder")

        self.context_menu.addAction(self.action1)
        self.context_menu.addAction(self.action2)
        self.context_menu.addSeparator()
        self.context_menu.addAction(self.action3)

        #connect action to functions
        self.action1.triggered.connect(self.action1_triggered)
        self.action2.triggered.connect(self.action2_triggered)
        self.action3.triggered.connect(self.action3_triggered)

    def contextMenuEvent(self, event):
        self.context_menu.exec_(event.globalPos())

    def action1_triggered(self):
        selection_name = self.objectName()
        selection = "mantraLgt"
        State.create_hdri_node(self, selection, selection_name)
        print(selection_name)

    def action2_triggered(self):
        selection_name = self.objectName()
        selection = "prmanLgt"
        State.create_hdri_node(self, selection, selection_name)

    def action3_triggered(self):
        selection_name = self.sender()
        hou.ui.showInFileBrowser(hdri_folder)

    #mouse event
    def enterEvent(self, event):
        self.mouseHover.emit(True)

    def leaveEvent(self, event):
        self.mouseHover.emit(False)

    #drag event
    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton:
            scene_viewer = hou.ui.paneTabOfType(hou.paneTabType.SceneViewer)
            scene_viewer.cd("/obj")
            scene_viewer.setCurrentState("Ak_Asset_Browser")
            drag = QDrag(self)
            mime = QMimeData()
            mime.setText(self.objectName())
            drag.setMimeData(mime)

            pixmap = QtGui.QPixmap(self.size())
            self.render(pixmap)
            drag.setPixmap(pixmap)
            drag.setMimeData(mime)
            drag.exec_(Qt.MoveAction)

