import hou
from PySide2 import QtNetwork
from PySide2 import QtWidgets, QtGui, QtCore
import json, requests


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
        self.parent().setPixmap(self.pixmap)


class MainAssetBrowserUI(QtWidgets.QWidget):
    def __init__(self):
        super(MainAssetBrowserUI, self).__init__()

        self.download_queue = QtNetwork.QNetworkAccessManager()

        #main layout
        main_layout = QtWidgets.QVBoxLayout()
        main_layout.setContentsMargins(0,0,0,0)

        icon_view = QtWidgets.QListWidget()
        icon_view.setViewMode(QtWidgets.QListWidget.IconMode)

        #Poly Haven API

        # https://cdn.polyhaven.com/asset_img/thumbs/hikers_cave.png
        
        hdriUrl = "https://api.polyhaven.com/assets?t=hdris"
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
            url = "https://cdn.polyhaven.com/asset_img/thumbs/" + key + ".png?height=" + str(thumb_size)

            thumb_img_lbl = QtWidgets.QLabel("Loading...")
            req = QtNetwork.QNetworkRequest(QtCore.QUrl(url))
            
            download = ImgDownloader(thumb_img_lbl, req)
            download.start_fetch(self.download_queue)
            
            item = QtWidgets.QListWidgetItem()
            item.setSizeHint(QtCore.QSize(thumb_size, thumb_size))
            #item.setIcon(QtGui.QIcon("D:\JOBS\YT\__Logos__\Ak Studio Stroke PNG logo.png"))
            icon_view.addItem(item)
            icon_view.setItemWidget(item, thumb_img_lbl)

        #thumbnail widget
        # img = QtGui.QImage()
        # img.loadFromData(requests.get("https://cdn.polyhaven.com/asset_img/thumbs/hikers_cave.png?height=200").content)
        # hdri_thumb_lbl = QtWidgets.QLabel("Loading")
        # hdri_thumb_lbl.setPixmap(QtGui.QPixmap(img))

        #add widgets to main layout
        main_layout.addWidget(QtWidgets.QPushButton("Hey There")) #testing btn
        main_layout.addWidget(icon_view)


           
        #final layout
        self.setLayout(main_layout)