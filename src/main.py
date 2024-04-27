import re
import time
import hou
from PySide2 import QtNetwork
from PySide2 import QtWidgets, QtGui, QtCore
from PySide2.QtUiTools import QUiLoader
from PySide2.QtCore import Qt
import json, requests, os
from .worker import Worker
from .flowLayout import FlowLayout

#get actual main.py file path
workpath = os.path.join(os.path.dirname(__file__))
#print(workpath + "\\ui\\mainUI.ui")


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
        self.ui = self.loader.load(workpath + "\\ui\\mainUI.ui")

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

        self.icon_size_slider.valueChanged.connect(self.set_icons)

        #setup for flowlayout
        self.widget = QtWidgets.QWidget()
        self.contentArea.setWidget(self.widget)


        self.icon_size = self.icon_size_slider.value()
        self.set_icons(self.icon_size)

        

    def set_icons(self, icon_size):
        print(icon_size)
        #Poly Haven API
        # https://cdn.polyhaven.com/asset_img/thumbs/hikers_cave.png
        
        # hdriUrl = "https://api.polyhaven.com/assets?t=hdris"
        hdriUrl = "https://api.polyhaven.com/assets?t=hdris&c=studio"
        r = requests.get(hdriUrl)
        self.data = json.loads(r.content)

        assets_view = FlowLayout(self.widget)

        for key in self.data.keys():

            self.btn = QtWidgets.QToolButton()
            self.btn.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
            self.btn.setFixedSize(QtCore.QSize(icon_size, icon_size))
            self.btn.setIconSize(QtCore.QSize(icon_size, icon_size))
            self.btn.setText(key.replace("_", " ").title())
            self.btn.setObjectName(key)

            url = "https://cdn.polyhaven.com/asset_img/thumbs/" + key + ".png?height=" + str(200)

            req = QtNetwork.QNetworkRequest(QtCore.QUrl(url))
            
            download = ImgDownloader(self.btn, req)
            download.start_fetch(self.download_queue)

            assets_view.addWidget(self.btn)
            
            #connect funtion to button
            self.btn.clicked.connect(self.asset_clicked)

            self.setLayout(self.main_layout)

            
           

    def asset_clicked(self):
        name = self.sender().objectName()
        print(name)

        tex_res = "1k"
        asset_fomat = "exr"
        asset_json = requests.get("https://api.polyhaven.com/files/" + name).json()
        # print(asset_json)
        self.url = asset_json["hdri"][tex_res][asset_fomat]["url"]
        self.file_size = asset_json["hdri"][tex_res][asset_fomat]["size"]

        local_file_name = os.path.dirname(workpath) + "\\downloads\\" + os.path.basename(self.url)
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
        print("Task Done!")


    
