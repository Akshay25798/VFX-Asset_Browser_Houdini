import sys
import traceback
from PySide2.QtCore import QRunnable, QObject, Slot
from PySide2.QtCore import Signal


class Signals(QObject):
    finished = Signal()
    error = Signal(tuple)
    result = Signal(object)
    progress = Signal(int)

class Worker(QRunnable):
    def __init__(self, n, *args, **kwargs):
        super().__init__()

        self.n = n
        self.args = args
        self.kwargs = kwargs
        self.signals = Signals()

        #add signals to kwargs
        self.kwargs["progress_callback"] = self.signals.progress

    @Slot()
    def run(self):
        try:
            result = self.n(*self.args, **self.kwargs)
        except:
            traceback.print_exc()
            exctype, value = sys.exc_info()[:2]
            self.signals.error.emit((exctype, value, traceback.format_exc()))
        else:
            self.signals.result.emit(result)
        finally:
            self.signals.finished.emit()
