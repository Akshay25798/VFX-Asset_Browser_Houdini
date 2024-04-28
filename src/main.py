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
#print(workpath + "\\ui\\mainUI.ui")

font_path = workpath + "\\assets\\fonts\\"
font_id = QtGui.QFontDatabase.addApplicationFont(font_path + "Roboto-Medium.ttf")
# print(QtGui.QFontDatabase.applicationFontFamilies(font_id))

ui_file_path = workpath + "\\ui\\mainUI.ui"

download_folder = os.path.dirname(workpath) + "\\downloads\\"

thumbnail_folder = download_folder + "thumbnails\\"


##


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




    ##--functions starts--

    def get_asset_type(self):
        #Poly Haven API
        # https://cdn.polyhaven.com/asset_img/thumbs/hikers_cave.png
        # hdriUrl = "https://api.polyhaven.com/assets?t=hdris"
        # texUrl = "https://api.polyhaven.com/assets?t=textures"
        # 3dModelUrl = "https://api.polyhaven.com/assets?t=models"
        # hdriUrl = "https://api.polyhaven.com/assets?t=hdris&c=studio"
        if self.asset_type.currentIndex() == 0:
            self.Url = "https://api.polyhaven.com/assets?t=hdris&c=studio"
        elif self.asset_type.currentIndex() == 1:
            self.Url = "https://api.polyhaven.com/assets?t=textures&c=plaster"
        elif self.asset_type.currentIndex() == 2:
            self.Url = "https://api.polyhaven.com/assets?t=models&c=rocks"
        else:
            self.Url = "https://api.polyhaven.com/assets?t=hdris&c=studio"
        self.clear_layout(self.assets_view)
        self.set_icons()
        

    def clear_layout(self, layout):
        while layout.count():
            child = layout.takeAt(0)
            print(child)
            if child.widget():
                child.widget().deleteLater()

    def set_icons(self, size=200):

        r = requests.get(self.Url)
        self.data = json.loads(r.content)

        for key in self.data.keys():
            btn = QtWidgets.QToolButton()
            btn.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)  
            btn.setFixedSize(QtCore.QSize(size, size))
            btn.setIconSize(QtCore.QSize(size, size))
            btn.setText(key.replace("_", " ").title())
            btn.setObjectName(key)
            btn.setStyleSheet("QToolButton{font-family: Roboto}")


            thumb_name = (("{0}.png".format(btn.objectName())))
            if not thumb_name in os.listdir(thumbnail_folder):

                url = "https://cdn.polyhaven.com/asset_img/thumbs/" + key + ".png?height=" + str(500)
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
            asset_json = requests.get("https://api.polyhaven.com/files/" + name).json()
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

    # def download_thumbnails(self):

    #     for key in url_dict:
    #         file_name = key.replace(' ', '_')
    #         img = Image.open(requests.get(url_dict[key], stream = True).raw)
    #         img.save(f'images/{file_name}.{img.format.lower()}')

    
