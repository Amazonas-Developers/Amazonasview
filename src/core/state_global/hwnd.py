from PySide6.QtCore import QTimer, QObject, Signal



class HwndState(QObject):

    change_hwnd = Signal(int)


    def __init__(self):
        super().__init__()
        self._hwnd = None



    def set_hwnd(self, hwnd: int):
        if hwnd != self._hwnd:
            self._hwnd = hwnd
            self.change_hwnd.emit(hwnd)

    
    def get_hwnd(self):
        return self._hwnd
    


hwndState = HwndState()