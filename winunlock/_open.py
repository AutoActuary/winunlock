import msvcrt
import ctypes
import os
import ctypes
from typing import Any, Union, IO
from os import PathLike
from pathlib import Path
from types import MethodType
from ._iotype import _IOType


def open(
    filename: Union[str, PathLike[str]], mode: str = "r", *args: Any, **kwargs: Any
) -> _IOType:
    """
    Opens a file with specified mode using Windows API to handle various locks.

    This function works similarly to the built-in `open` but can handle files locked
    by programs such as OneDrive. It bypasses locks for reading using the correct
    combination of flags on the Windows API.

    Args:
        filename (str): The path to the file to be opened.
        mode (str, optional): The mode in which the file is opened. Supports 'r', 'w', 'rw',
            'rb', 'wb', 'a', and 'ab'. Defaults to 'r'.
        *args: Variable list of arguments passed to os.fdopen().
        **kwargs: Arbitrary keyword arguments passed to os.fdopen().

    Returns:
        file: A file object.

    Raises:
        ValueError: If the provided mode is not supported.
        FileNotFoundError: If the file does not exist.
        PermissionError: If permission is denied to access the file.
        FileExistsError: If the file already exists and mode is set to create.
        IsADirectoryError: If the provided filename is a directory.
        OSError: For generic OS errors and errors thrown by os.fdopen.
        ctypes.WinError: For other Windows API-related errors.

    Example:
        >>> with open("locked_file.txt", "r") as f:
        >>>     content = f.read()

    Note:
        This function is designed for Windows and uses the Windows API. It is not cross-platform.

    """
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

    # Ignore to avoid mypy error on Linux machines
    CreateFileW = ctypes.windll.kernel32.CreateFileW  # type: ignore

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
        # Ignore to avoid mypy error on Linux machines
        error_code = ctypes.GetLastError()  # type: ignore

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
            # Ignore to avoid mypy error on Linux machines
            raise ctypes.WinError()  # type: ignore

    try:
        # for 'append' mode, you'd also need to move the file pointer to the end
        if mode in {"a", "ab"}:
            # Ignore to avoid mypy error on Linux machines
            ctypes.windll.kernel32.SetFilePointer(hfile, 0, None, FILE_END)  # type: ignore

        # Convert the Windows handle into a C runtime file descriptor
        # Ignore to avoid mypy error on Linux machines
        fd = msvcrt.open_osfhandle(hfile, os.O_BINARY if "b" in mode else os.O_TEXT)  # type: ignore

        # Create a Python file object from the file descriptor
        file = os.fdopen(fd, mode, *args, **kwargs)
    except:
        # Close the handle if an exception occurred
        # Ignore to avoid mypy error on Linux machines
        ctypes.windll.kernel32.CloseHandle(hfile)  # type: ignore
        raise

    # Monkeypatch the file object to include hfile as a closure and
    # apply `CloseHandle(hfile)` when closing the file
    original_exit = file.__exit__

    def __exit__(self: IO[Any], *args: Any) -> None:
        original_exit(*args)
        # Ignore to avoid mypy error on Linux machines
        ctypes.windll.kernel32.CloseHandle(hfile)  # type: ignore

    setattr(
        file,
        "__exit__",
        MethodType(__exit__, file),
    )

    return file
