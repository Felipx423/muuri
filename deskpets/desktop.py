"""Select the desktop integration without importing Win32 on macOS."""
import sys

IS_WINDOWS = sys.platform == "win32"

if IS_WINDOWS:
    from .windows_API import Windows as Desktop
else:
    from .macos_api import MacOS as Desktop
