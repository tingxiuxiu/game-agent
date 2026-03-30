import time
import pyautogui
from PIL import Image
from typing import Optional, Tuple, List
import ctypes
from ctypes import wintypes

from .logger import get_logger

logger = get_logger(__name__)

pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.3

user32 = ctypes.windll.user32

class RECT(ctypes.Structure):
    _fields_ = [
        ("left", wintypes.LONG),
        ("top", wintypes.LONG),
        ("right", wintypes.LONG),
        ("bottom", wintypes.LONG)
    ]

class ScreenController:
    def __init__(self, default_delay: float = 0.3, retry_count: int = 3):
        self.default_delay = default_delay
        self.retry_count = retry_count
        pyautogui.PAUSE = default_delay
    
    def _retry_operation(self, func, *args, **kwargs):
        last_exception = None
        for attempt in range(self.retry_count):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                time.sleep(self.default_delay)
        raise last_exception
    
    def move_to(self, x: int, y: int, duration: float = 0.25):
        logger.debug(f"Moving mouse to ({x}, {y}) with duration {duration}s")
        self._retry_operation(pyautogui.moveTo, x, y, duration=duration)
        time.sleep(self.default_delay)
    
    def click_at(self, x: int, y: int, button: str = 'left', clicks: int = 1, interval: float = 0.1):
        logger.debug(f"Clicking at ({x}, {y}), button={button}, clicks={clicks}")
        self._retry_operation(pyautogui.click, x, y, button=button, clicks=clicks, interval=interval)
        time.sleep(self.default_delay)
    
    def press_key(self, key: str, presses: int = 1, interval: float = 0.1):
        logger.debug(f"Pressing key {key} {presses} times with interval {interval}s")
        self._retry_operation(pyautogui.press, key, presses=presses, interval=interval)
        time.sleep(self.default_delay)
    
    def type_text(self, text: str, interval: float = 0.05):
        logger.debug(f"Typing text: {text[:50]}... with interval {interval}s")
        self._retry_operation(pyautogui.typewrite, text, interval=interval)
        time.sleep(self.default_delay)
    
    def hotkey(self, *keys: str):
        logger.debug(f"Pressing hotkey: {'+'.join(keys)}")
        self._retry_operation(pyautogui.hotkey, *keys)
        time.sleep(self.default_delay)
    
    def screenshot(self, region: Optional[Tuple[int, int, int, int]] = None) -> Image.Image:
        logger.debug(f"Taking screenshot, region={region}")
        return self._retry_operation(pyautogui.screenshot, region=region)
    
    def save_screenshot(self, filepath: str, region: Optional[Tuple[int, int, int, int]] = None):
        logger.debug(f"Saving screenshot to {filepath}")
        img = self.screenshot(region=region)
        img.save(filepath)
    
    def find_window(self, title: str) -> Optional[int]:
        logger.debug(f"Finding window with title containing: {title}")
        def enum_windows_proc(hwnd, lParam):
            length = user32.GetWindowTextLengthW(hwnd)
            if length > 0:
                buffer = ctypes.create_unicode_buffer(length + 1)
                user32.GetWindowTextW(hwnd, buffer, length + 1)
                if title in buffer.value:
                    lParam.append(hwnd)
            return True
        
        hwnds = []
        WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, ctypes.py_object)
        user32.EnumWindows(WNDENUMPROC(enum_windows_proc), hwnds)
        if hwnds:
            logger.debug(f"Found window, hwnd={hwnds[0]}")
            return hwnds[0]
        logger.debug("No window found")
        return None
    
    def get_window_rect(self, hwnd: int) -> Optional[Tuple[int, int, int, int]]:
        logger.debug(f"Getting window rect for hwnd={hwnd}")
        rect = RECT()
        if user32.GetWindowRect(hwnd, ctypes.byref(rect)):
            return (rect.left, rect.top, rect.right - rect.left, rect.bottom - rect.top)
        return None
    
    def activate_window(self, hwnd: int):
        logger.debug(f"Activating window, hwnd={hwnd}")
        user32.SetForegroundWindow(hwnd)
        user32.SetFocus(hwnd)
        time.sleep(self.default_delay)
    
    def get_screen_size(self) -> Tuple[int, int]:
        return pyautogui.size()
    
    def get_mouse_position(self) -> Tuple[int, int]:
        return pyautogui.position()
