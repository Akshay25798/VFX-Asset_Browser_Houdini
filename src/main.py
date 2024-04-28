import re
import time
from tkinter import font
import hou
from PySide2 import QtNetwork
from PySide2 import QtWidgets, QtGui, QtCore
from PySide2.QtUiTools import QUiLoader
from PySide2.QtCore import Qt
import json, requests, os
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


##

class ImgDownloader(QtCore.QObject):
    def __init__(self, parent, req):
        self.req = req
        self.pixmap = QtGui.QPixmap()
        super(ImgDownloader, self).__init__(parent)

    def start_fetch(self, net_mgr):
        self.fetch_task = net_mgr.get(self.req)
        self.fetch_task.finished.connect(self.resolve_fetch)

    def resolve_fetch(self):
        the_reply = self.fetch_task.readAll()
        self.set_widget_image(the_reply)

    def set_widget_image(self, img_binary):
        self.pixmap.loadFromData(img_binary)
        icon = QtGui.QIcon()
        icon.addPixmap(self.pixmap)
        self.parent().setIcon(icon)
        # self.parent().setPixmap(self.pixmap)


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
        self.statu_bar = self.ui.statusBar
        self.icon_size_slider = self.ui.iconSize
        self.scrol_area_splitter = self.ui.scrollAreaSplitter

        #main layout and parameters
        self.main_layout = QtWidgets.QVBoxLayout()
        self.main_layout.setContentsMargins(0,0,0,0)
        self.main_layout.addWidget(self.ui)

        #setup for flowlayout
        self.widget = QtWidgets.QWidget()
        self.contentArea.setWidget(self.widget)

        #set property
        self.progress_bar.setProperty("visible", False)
        self.set_icons()
        self.icon_size_slider.valueChanged.connect(self.set_icons_size)

    def set_icons(self, size=200):
        # print(size)
        #Poly Haven API
        # https://cdn.polyhaven.com/asset_img/thumbs/hikers_cave.png
        # hdriUrl = "https://api.polyhaven.com/assets?t=hdris"
        hdriUrl = "https://api.polyhaven.com/assets?t=hdris&c=studio"
        r = requests.get(hdriUrl)
        self.data = json.loads(r.content)

        assets_view = FlowLayout(self.widget)

        for key in self.data.keys():
            btn = QtWidgets.QToolButton()
            btn.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
            btn.setFixedSize(QtCore.QSize(size, size))
            btn.setIconSize(QtCore.QSize(size, size))
            btn.setText(key.replace("_", " ").title())
            btn.setObjectName(key)
            btn.setStyleSheet("QToolButton{font-family: Roboto}")

            url = "https://cdn.polyhaven.com/asset_img/thumbs/" + key + ".png?height=" + str(500)

            req = QtNetwork.QNetworkRequest(QtCore.QUrl(url))
            
            download = ImgDownloader(btn, req)
            download.start_fetch(self.download_queue)

            assets_view.addWidget(btn)
            
            #connect funtion to button
            btn.clicked.connect(self.asset_clicked)

            self.setLayout(self.main_layout)


    def set_icons_size(self, size):
        icons = self.contentArea.findChildren(QtWidgets.QToolButton)
        font_size = int(5*(int(size)*0.01))

        for icon in icons:
            icon.setFixedSize(QtCore.QSize(size, size))
            icon.setIconSize(QtCore.QSize(size, size))
            icon.setStyleSheet("QToolButton{font-size: %spt}"%(str(font_size)))
        self.statu_bar.setText("icon size : " + str(size))
        
           

    def asset_clicked(self):
        name = self.sender().objectName()
        tex_res = "1k"
        asset_fomat = "exr"
        path_to_check = "{0}{1}_{2}.{3}".format(download_folder, name, tex_res, asset_fomat)
        # print(path_to_check)
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
        self.statu_bar.setText(str(os.path.basename(self.url)) + ", Downloading : " + str(n))

    def print_output(self, s):
        print("Result : ", s)

    def thread_complete(self):
        self.statu_bar.setText(str(os.path.basename(self.url)))
        self.progress_bar.setProperty("visible", False)
        # print("Task Done!")


    
