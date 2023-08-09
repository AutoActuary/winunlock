import msvcrt
import ctypes
import os
import ctypes
import locate
from pathlib import Path


def open_locked(filename, mode="r", *args, **kwargs):
    GENERIC_READ = 0x80000000
    GENERIC_WRITE = 0x40000000
    FILE_SHARE_READ = 1
    FILE_SHARE_WRITE = 2
    FILE_SHARE_DELETE = 4

    OPEN_EXISTING = 3
    CREATE_ALWAYS = 2
    OPEN_ALWAYS = 4
    FILE_END = 2

    access_flags = {
        "r": GENERIC_READ,
        "w": GENERIC_WRITE,
        "rw": GENERIC_READ | GENERIC_WRITE,
        "rb": GENERIC_READ,
        "wb": GENERIC_WRITE,
        "a": GENERIC_WRITE,  # for 'append' mode
        "ab": GENERIC_WRITE,  # for 'append' binary mode
    }

    dispositions = {
        "r": OPEN_EXISTING,
        "w": CREATE_ALWAYS,
        "rw": OPEN_ALWAYS,
        "rb": OPEN_EXISTING,
        "wb": CREATE_ALWAYS,
        "a": OPEN_ALWAYS,  # for 'append' mode
        "ab": OPEN_ALWAYS,  # for 'append' binary mode
    }

    CreateFileW = ctypes.windll.kernel32.CreateFileW

    access_mode = access_flags.get(mode)
    if access_mode is None:
        raise ValueError(
            f"Invalid mode '{mode}', only 'r', 'w', 'rw', 'rb', 'wb', 'a', and 'ab' are supported"
        )

    disposition = dispositions.get(mode)
    if disposition is None:
        raise ValueError(
            f"Invalid mode '{mode}', only 'r', 'w', 'rw', 'rb', 'wb', 'a', and 'ab' are supported"
        )

    hfile = CreateFileW(
        str(Path(filename)),
        access_mode,
        FILE_SHARE_READ | FILE_SHARE_WRITE | FILE_SHARE_DELETE,
        None,
        disposition,
        0,
        None,
    )

    UNKNOWN_ERROR = 0
    INVALID_HANDLE_VALUE = -1
    ERROR_FILE_NOT_FOUND = 2
    ERROR_ACCESS_DENIED = 5
    ERROR_INVALID_PARAMETER = 87
    ERROR_FILE_EXISTS = 80
    ERROR_ALREADY_EXISTS = 183
    ERROR_DIRECTORY = 267

    if hfile == INVALID_HANDLE_VALUE:
        # Get the last error code
        error_code = ctypes.GetLastError()

        if error_code == ERROR_FILE_NOT_FOUND:
            raise FileNotFoundError(f"No such file or directory: '{filename}'")
        elif error_code == ERROR_ACCESS_DENIED:
            raise PermissionError("Permission denied: '{}'".format(filename))
        elif error_code == ERROR_INVALID_PARAMETER:
            raise ValueError("Invalid parameter")
        elif error_code == ERROR_FILE_EXISTS or error_code == ERROR_ALREADY_EXISTS:
            raise FileExistsError("File already exists: '{}'".format(filename))
        elif error_code == ERROR_DIRECTORY:
            raise IsADirectoryError("Is a directory: '{}'".format(filename))
        elif error_code == UNKNOWN_ERROR:
            raise OSError("Unknown error")
        else:
            raise ctypes.WinError()

    try:
        # for 'append' mode, you'd also need to move the file pointer to the end
        if mode in {"a", "ab"}:
            ctypes.windll.kernel32.SetFilePointer(hfile, 0, None, FILE_END)

        # Convert the Windows handle into a C runtime file descriptor
        fd = msvcrt.open_osfhandle(hfile, os.O_BINARY if "b" in mode else os.O_TEXT)

        # Create a Python file object from the file descriptor
        file = os.fdopen(fd, mode, *args, **kwargs)
    except:
        # Close the handle if an exception occurred
        ctypes.windll.kernel32.CloseHandle(hfile)
        raise

    # Monkeypatch the file object to do `CloseHandle(hfile)` when closing the file
    original_file_exit = file.__exit__

    def __exit__(self, *args):
        original_file_exit(*args)
        ctypes.windll.kernel32.CloseHandle(self.hfile)

    file.__exit__ = __exit__

    return file
