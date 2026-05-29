import win32gui
import os
from dotenv import load_dotenv


load_dotenv()
name_my_window = os.getenv('name_project', 'App')


def open_windows_windows(): 
    windows = []
    def enum_windows_proc(hwnd, param):

        if win32gui.IsWindowVisible(hwnd) and win32gui.GetWindowText(hwnd):

            if(name_my_window != win32gui.GetWindowText(hwnd)): windows.append({
                'hwnd': hwnd,
                'title': win32gui.GetWindowText(hwnd),
                'class': win32gui.GetClassName(hwnd)
            })
        return True
    
    win32gui.EnumWindows(enum_windows_proc, None)
    return windows
