import hou
from PySide2 import QtNetwork
from PySide2 import QtWidgets, QtGui, QtCore
from PySide2.QtUiTools import QUiLoader
from PySide2.QtCore import Qt
import json, requests, os
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

        self.download_queue = QtNetwork.QNetworkAccessManager()

        #load ui file
        self.loader = QUiLoader()
        self.ui = self.loader.load(workpath + "\\ui\\mainUI.ui")

        self.contentArea = self.ui.ContantArea

        #main layout
        main_layout = QtWidgets.QVBoxLayout()
        main_layout.setContentsMargins(0,0,0,0)
        main_layout.addWidget(self.ui)

        #setup for flowlayout
        self.widget = QtWidgets.QWidget()
        self.contentArea.setWidget(self.widget)

        assets_view = FlowLayout(self.widget)

        # icon_view = QtWidgets.QListWidget()
        # icon_view.setViewMode(QtWidgets.QListWidget.IconMode)

        #Poly Haven API

        # https://cdn.polyhaven.com/asset_img/thumbs/hikers_cave.png
        
        # hdriUrl = "https://api.polyhaven.com/assets?t=hdris"
        hdriUrl = "https://api.polyhaven.com/assets?t=hdris&c=studio"
        r = requests.get(hdriUrl)
        data = json.loads(r.content)
        thumb_size = 200

        urls = [

           " https://cdn.polyhaven.com/asset_img/thumbs/hotel_room.png",
           "https://cdn.polyhaven.com/asset_img/thumbs/snowy_forest.png",
           "https://cdn.polyhaven.com/asset_img/thumbs/urban_courtyard.png",
           "https://cdn.polyhaven.com/asset_img/thumbs/sisulu.png",
           "https://cdn.polyhaven.com/asset_img/thumbs/piazza_san_marco.png"
        ] 

        for key in data.keys():
            btn = QtWidgets.QToolButton()
            btn.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
            btn.setFixedSize(QtCore.QSize(thumb_size, thumb_size))
            btn.setIconSize(QtCore.QSize(thumb_size, thumb_size))
            btn.setText(key.replace("_", " ").title())
            btn.setObjectName(key)

            #btn.setIcon(QtGui.QIcon("D:\JOBS\YT\__Logos__\Ak Studio Stroke PNG logo.png"))


            url = "https://cdn.polyhaven.com/asset_img/thumbs/" + key + ".png?height=" + str(thumb_size)

            req = QtNetwork.QNetworkRequest(QtCore.QUrl(url))
            
            download = ImgDownloader(btn, req)
            download.start_fetch(self.download_queue)

            assets_view.addWidget(btn)

            #connect funtion to button
            btn.clicked.connect(self.asset_clicked)
            

            
           
        #final layout
        self.setLayout(main_layout)

    def asset_clicked(self):
        name = self.sender().objectName()
        print(name)