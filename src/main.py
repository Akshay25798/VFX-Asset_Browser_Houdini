import hou
from PySide2 import QtNetwork
from PySide2 import QtWidgets, QtGui, QtCore
from PySide2.QtUiTools import QUiLoader
from PySide2.QtCore import Qt
import json, requests, os

import layout
from .worker import Worker
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

        # self.pixmap.loadFromData(img_binary) #load directly form web/api
        # icon = QtGui.QIcon()
        # icon.addPixmap(self.pixmap)
        # self.parent().setIcon(icon)



class MainAssetBrowserUI(QtWidgets.QWidget):
    def __init__(self):
        super(MainAssetBrowserUI, self).__init__()
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

        #set property
        self.progress_bar.setProperty("visible", False)
        self.get_asset_type()
        # self.set_icons()
        self.asset_type.currentIndexChanged.connect(self.get_asset_type)
        self.icon_size_slider.valueChanged.connect(self.set_icons_size)
        self.tex_res.currentIndexChanged.connect(self.check_asset_download_status)
        self.asset_format.currentIndexChanged.connect(self.check_asset_download_status)
        self.asset_catagories.currentIndexChanged.connect(self.get_asset_type)

        




    ##--functions starts--

    def get_asset_type(self):
        if len(os.listdir(json_folder))==0:
            self.write_json_to_local()

        if self.asset_type.currentIndex() == 0:
            json_foder_index = json_folder + "hdris.json"
            self.get_cagagories("hdris")
        elif self.asset_type.currentIndex() == 1:
            json_foder_index = json_folder + "models.json"
            self.get_cagagories("models")
        elif self.asset_type.currentIndex() == 2:
            json_foder_index = json_folder + "textures.json"
            self.get_cagagories("textures")
        else:
            json_foder_index = "https://api.polyhaven.com/assets?t=hdris&c=studio"

        self.clear_layout(self.assets_view)
        self.set_icons(json_foder_index)
        
    def get_cagagories(self, asset_type="hdris"):
        catagory_json = json_folder + asset_type + "_catagories.json"
        self.asset_catagories.clear()
        with open(catagory_json, "r") as read_content:
            d = json.load(read_content)
            catagory = d.keys()
            for i, key in enumerate(catagory):
                self.asset_catagories.insertItem(i, key)
        self.asset_catagories.setCurrentIndex(1)


    def write_json_to_local(self):
        assets_types = ["hdris", "textures", "models"]
        for type in assets_types:
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
            if child.widget():
                child.widget().deleteLater()

    def set_icons(self, json_foder_index, size=200):
        catagory = self.asset_catagories.currentText()
        with open(json_foder_index, "r") as read_content:
            d = json.load(read_content)
            for key in d.keys():
                if catagory in (d[key]["categories"]):
                    # print(key)

        # with open(json_foder_index, "r") as read_content: #ping the local json
        #     self.data = json.load(read_content)
        #     # print(d.keys())

        # for key in self.data.keys():
                    btn = QtWidgets.QToolButton()
                    btn.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)  
                    btn.setFixedSize(QtCore.QSize(size, size))
                    btn.setIconSize(QtCore.QSize(size, size))
                    btn.setText(key.replace("_", " ").title())
                    btn.setObjectName(key)
                    btn.setStyleSheet("QToolButton{font-family: Roboto}")


                    thumb_name = (("{0}.png".format(btn.objectName())))
                    if not thumb_name in os.listdir(thumbnail_folder):

                        url = thumb_url + key + ".png?height=" + str(500)
                        req = QtNetwork.QNetworkRequest(QtCore.QUrl(url))
                        
                        download = IconDownloader(btn, req)
                        download.start_fetch(self.download_queue)
                        self.assets_view.addWidget(btn)
                        self.assets_view.setSpacing(4)
                        self.setLayout(self.main_layout)

                    #get icons form local thumbnail folder
                    get_local_thumb = thumbnail_folder + thumb_name
                    icon = QtGui.QIcon()
                    icon.addPixmap(get_local_thumb)
                    btn.setIcon(icon)

                    #icon add to content area
                    self.assets_view.addWidget(btn)
                    self.setLayout(self.main_layout)

                    #connect funtion to button
                    btn.clicked.connect(self.asset_clicked)
                    self.set_icons_size(200)


    def check_asset_download_status(self):
        icons = self.contentArea.findChildren(QtWidgets.QToolButton)
        border_size = 3
        for icon in icons:
            local_asset_name = (("{0}_{1}.{2}".format(icon.objectName(), self.tex_res.currentText(), self.asset_format.currentText())))
            if local_asset_name in os.listdir(download_folder):
                icon.setStyleSheet("QToolButton{border: %spx solid #32CD32}"%(border_size))
            else:
                icon.setStyleSheet("QToolButton{border: %spx solid #32CD32}"%(0))

    def set_icons_size(self, size):
        icons = self.contentArea.findChildren(QtWidgets.QToolButton)
        font_size = int(5*(int(size)*0.01))
        border_size = 3

        for icon in icons:
            icon.setFixedSize(QtCore.QSize(size, size))
            icon.setIconSize(QtCore.QSize(size, size))
            icon.setStyleSheet("QToolButton{font-size: %spt}"%(str(font_size)))

            local_asset_name = (("{0}_{1}.{2}".format(icon.objectName(), self.tex_res.currentText(), self.asset_format.currentText())))
            if local_asset_name in os.listdir(download_folder):
                icon.setStyleSheet("QToolButton{border: %spx solid #32CD32; font-size: %spt}"%(border_size, str(font_size)))
            else:
                icon.setStyleSheet("QToolButton{border: %spx solid #32CD32; font-size: %spt}"%(0, str(font_size)))
        self.status_bar.setText("icon size : " + str(size))
        

    def asset_clicked(self):
        name = self.sender().objectName()
        tex_res = self.tex_res.currentText()
        asset_fomat = self.asset_format.currentText()
        path_to_check = "{0}{1}_{2}.{3}".format(download_folder, name, tex_res, asset_fomat)
        # print(tex_res)
        if not os.path.exists(path_to_check):
            self.progress_bar.setProperty("visible", True)
            self.progress_bar.setValue(0)
            asset_json = requests.get(asset_url + name).json()
            # print(asset_json)
            self.url = asset_json["hdri"][tex_res][asset_fomat]["url"]
            self.file_size = asset_json["hdri"][tex_res][asset_fomat]["size"]

            local_file_name = download_folder + os.path.basename(self.url)
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
        # print("Progress : " , n)
        i = self.progress_bar.setValue(n)
        self.status_bar.setText(str(os.path.basename(self.url)) + ", Downloading : " + str(n))

    def print_output(self, s):
        # print("Result : ", s)
        pass

    def thread_complete(self):
        self.status_bar.setText(str(os.path.basename(self.url)))
        self.progress_bar.setProperty("visible", False)
        self.check_asset_download_status()
        # print("Task Done!")


    
