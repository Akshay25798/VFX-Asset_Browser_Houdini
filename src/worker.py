import re
from unittest import result
from PySide2 import QtCore
from PySide2.QtCore import Slot
import sys
import traceback

class WorkerSignal(QtCore.QObject):
    finished = QtCore.Signal()
    error = QtCore.Signal(tuple)
    result = QtCore.Signal(object)
    prograss = QtCore.Signal(int)

class Worker(QtCore.QRunnable):
    #wroker thread
    def __init__(self, fn, *args, **kwargs):
        super(Worker, self).__init__()

        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.signal = WorkerSignal()

        #add signals to kwargs
        self.kwargs["process_callback"] = self.signals.prograss

    @Slot()
    def run(self):
        try:
            result = self.fn(*self.args, **self.kwargs)
        except:
            traceback.print_exc()
            exctype, value = sys.exc_info()[:2]
            self.signal.error.emit((exctype, value, traceback.format_exc()))
        else:
            self.signal.result.emit(result)
        finally:
            self.signal.finished.emit()