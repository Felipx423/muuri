import ctypes
import hashlib
import sys
from ctypes import wintypes


class SingleInstance:
    """One application per session on Windows, or per user on macOS."""

    def __init__(self, name="Local\\PetlayerDeskPetsMuuri"):
        self.name = name
        self.handle = None
        self.lock = None
        if sys.platform != "win32":
            return
        self.kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        self.kernel32.CreateMutexW.argtypes = [ctypes.c_void_p, wintypes.BOOL, wintypes.LPCWSTR]
        self.kernel32.CreateMutexW.restype = wintypes.HANDLE
        self.kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
        self.kernel32.CloseHandle.restype = wintypes.BOOL

    def acquire(self):
        if sys.platform != "win32":
            from PyQt6.QtCore import QLockFile
            from .config_io import configuration_dir
            folder = configuration_dir() / "locks"
            folder.mkdir(parents=True, exist_ok=True)
            filename = hashlib.sha256(self.name.encode("utf-8")).hexdigest() + ".lock"
            self.lock = QLockFile(str(folder / filename))
            self.lock.setStaleLockTime(0)
            return self.lock.tryLock(0)
        handle = self.kernel32.CreateMutexW(None, False, self.name)
        error = ctypes.get_last_error()
        if not handle:
            raise ctypes.WinError(error)
        if error == 183:  # ERROR_ALREADY_EXISTS
            self.kernel32.CloseHandle(handle)
            return False
        self.handle = handle
        return True

    def close(self):
        if self.lock is not None:
            self.lock.unlock()
            self.lock = None
        if self.handle is not None:
            self.kernel32.CloseHandle(self.handle)
            self.handle = None
