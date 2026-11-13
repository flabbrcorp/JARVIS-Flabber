"""Associate the Jarvis window with its Windows launcher."""
import ctypes
from ctypes import wintypes
from uuid import UUID


class PropertyKey(ctypes.Structure):
    _fields_ = [("format", ctypes.c_byte * 16), ("id", wintypes.DWORD)]


class PropertyValue(ctypes.Structure):
    _fields_ = [
        ("type", ctypes.c_ushort), ("reserved", ctypes.c_ushort * 3),
        ("text", ctypes.c_wchar_p), ("padding", ctypes.c_void_p),
    ]


def set_taskbar_identity(hwnd, launcher):
    store = ctypes.c_void_p()
    iid = (ctypes.c_byte * 16).from_buffer_copy(UUID("886d8eeb-8cf2-4446-8d02-cdba1dbdcf99").bytes_le)
    get_store = ctypes.windll.shell32.SHGetPropertyStoreForWindow
    get_store.argtypes = [wintypes.HWND, ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p)]
    get_store.restype = ctypes.HRESULT
    get_store(hwnd, iid, ctypes.byref(store))
    table = ctypes.cast(store, ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p)))[0]
    release = ctypes.WINFUNCTYPE(wintypes.ULONG, ctypes.c_void_p)(table[2])
    set_value = ctypes.WINFUNCTYPE(
        ctypes.HRESULT, ctypes.c_void_p, ctypes.POINTER(PropertyKey), ctypes.POINTER(PropertyValue)
    )(table[6])
    guid = (ctypes.c_byte * 16).from_buffer_copy(UUID("9f4c2855-9f79-4b39-a8d0-e1d42de1d5f3").bytes_le)
    try:
        for property_id, text in (
            (2, f'"{launcher}"'),
            (3, f"{launcher},0"),
            (4, "Jarvis Desktop"),
            (5, "Jarvis.Desktop"),
        ):
            key = PropertyKey(guid, property_id)
            value = PropertyValue(type=31, text=text)
            set_value(store, ctypes.byref(key), ctypes.byref(value))
    finally:
        release(store)
