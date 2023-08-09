import unittest
import random
import string
import locate
from pathlib import Path
import os
import tempfile
import uuid
import time
import psutil
import shutil
import pythoncom
import win32com.client
import win32process
import win32com
import ctypes
import multiprocessing
with locate.prepend_sys_path(".."):
    from winunlock import open as winunlock_open
    from winunlock import monkeypatch_open


# Note that this type of lock is still too strogn for our reading function
def lock_file(filename):
    GENERIC_READ = 0x80000000
    GENERIC_WRITE = 0x40000000
    OPEN_EXISTING = 3

    CreateFile = ctypes.windll.kernel32.CreateFileW

    hfile = CreateFile(
        filename,
        GENERIC_READ | GENERIC_WRITE,  # open for reading and writing
        0,  # no sharing
        None,
        OPEN_EXISTING,
        0,
        None,
    )
    if hfile == -1:
        raise ctypes.WinError()

    # Keep the process running and holding the lock
    while True:
        time.sleep(1)


class GenerateLockFile:
    def __init__(self):
        self.temp_filename_path = None
        self.process = None

    def __enter__(self):
        # create a temporary file
        self.temp_filename_path = Path(tempfile.gettempdir()) / f"{uuid.uuid4()}.txt"
        with open(self.temp_filename_path, "w") as temp_file:
            temp_file.write("This is a temporary file.")

        # open the temporary file in a new lock_file process
        self.process = multiprocessing.Process(
            target=lock_file, args=(str(self.temp_filename_path),)
        )
        self.process.start()

        # wait for lock_file to create the lock
        i = 0
        while (i := i + 1) != 50 and self.process.is_alive():
            time.sleep(0.1)

        if not self.process.is_alive():
            raise Exception("Could not create lock file")

        # return the lock file path
        return self.temp_filename_path

    def __exit__(self, *args):
        # terminate the lock_file process
        self.process.terminate()

        # delete the temporary file
        i = 0
        while (i := i + 1) != 50:
            try:
                os.remove(self.temp_filename_path)
                break
            except PermissionError:
                time.sleep(0.1)

        if i == 50:
            raise Exception("Could not delete temporary file")


class GenerateLockFileUsingExcel:
    def __init__(self):
        self.excel_path = locate.this_dir() / "example.xlsx"
        self.temp_excel_path = None
        self.process = None

    def __enter__(self):
        # copy the Excel file to a temporary location
        temp_excel_name = f"{uuid.uuid4()}.xlsx"
        self.temp_excel_path = Path(tempfile.gettempdir()) / temp_excel_name
        shutil.copy(self.excel_path, self.temp_excel_path)

        # open the temporary Excel file in a new Excel process
        pythoncom.CoInitialize()  # Initialize the COM library
        excel = win32com.client.DispatchEx(
            "Excel.Application"
        )  # creates a new instance of Excel
        excel.Visible = 0  # makes Excel hidden
        excel.Workbooks.Open(str(self.temp_excel_path))  # opens the workbook

        # Get the main thread ID and process ID of the Excel instance
        hndl = excel.Hwnd
        _, pid = win32process.GetWindowThreadProcessId(hndl)
        self.process = psutil.Process(pid)

        # wait for Excel to create the lock file
        lock_file_name = f"~${self.temp_excel_path.stem}.xlsx"
        lock_file_path = Path(tempfile.gettempdir()) / lock_file_name

        i = 0
        while (i := i + 1) != 50 and not lock_file_path.exists():
            time.sleep(0.1)

        if not lock_file_path.exists():
            raise Exception("Could not create lock file")

        # return the lock file path
        return lock_file_path

    def __exit__(self, *args):
        # close the Excel process
        p = psutil.Process(self.process.pid)
        p.terminate()

        # wait for Excel to remove the lock file
        lock_file_name = f"~${self.temp_excel_path.stem}.xlsx"
        lock_file_path = Path(tempfile.gettempdir()) / lock_file_name

        i = 0
        while (i := i + 1) != 50 and lock_file_path.exists():
            time.sleep(0.1)

        if lock_file_path.exists():
            raise Exception("Could not exit Excel process")

        # delete the temporary Excel file
        os.remove(self.temp_excel_path)


class TestOpenLockedWithExcelLock(unittest.TestCase):
    def setUp(self):
        self.xl = GenerateLockFileUsingExcel()
        self.fname = self.xl.__enter__()

    def tearDown(self):
        self.xl.__exit__(None, None, None)

    def test_read_text_file_with_open(self):
        # with the correct error
        with self.assertRaises(PermissionError):
            with open(
                self.fname,
                "r",
            ) as f:
                pass

    def test_read_text_file_with_winunlock_open(self):
        # success without error
        with winunlock_open(
            self.fname,
            "r",
        ) as f:
            f.read()

    def test_monkeypatch_open(self):
        # success without error
        with monkeypatch_open():
            with open(
                self.fname,
                "r",
            ) as f:
                f.read()


class TestOpenLockedWithLock(unittest.TestCase):
    def setUp(self):
        self.glf = GenerateLockFile()
        self.fname = self.glf.__enter__()

    def tearDown(self):
        self.glf.__exit__(None, None, None)

    def test_read_text_file_with_open(self):
        # with the correct error
        with self.assertRaises(PermissionError):
            with open(
                self.fname,
                "r",
            ) as f:
                pass

    # TODO: find a way to read this locked file
    """
    def test_read_text_file_with_winunlock_open(self):
        # success without error
        with winunlock_open(
            self.fname,
            "r",
        ) as f:
            f.read()
    """

class TestOpenLocked(unittest.TestCase):
    def random_string(self, length):
        return "".join(random.choice(string.ascii_letters) for _ in range(length))

    def test_read_text_file(self):
        # create a temp file with some text
        filename = tempfile.mktemp()
        with open(filename, "w") as f:
            f.write("hello world")

        # try reading it with winunlock_open
        with winunlock_open(filename, "r") as f:
            data = f.read()

        self.assertEqual(data, "hello world")

        # clean up
        os.remove(filename)

    def test_read_binary_file(self):
        # create a temp file with some bytes
        filename = tempfile.mktemp()
        with open(filename, "wb") as f:
            f.write(b"\x00\x01\x02\x03\x04")

        # try reading it with winunlock_open
        with winunlock_open(filename, "rb") as f:
            data = f.read()

        self.assertEqual(data, b"\x00\x01\x02\x03\x04")

        # clean up
        os.remove(filename)

    def test_write_text_file(self):
        filename = tempfile.mktemp()

        # try writing to it with winunlock_open
        with winunlock_open(filename, "w") as f:
            f.write("hello world")

        # check that the file contains the correct data
        with open(filename, "r") as f:
            data = f.read()

        self.assertEqual(data, "hello world")

        # clean up
        os.remove(filename)

    def test_write_binary_file(self):
        filename = tempfile.mktemp()

        # try writing to it with winunlock_open
        with winunlock_open(filename, "wb") as f:
            f.write(b"\x00\x01\x02\x03\x04")

        # check that the file contains the correct data
        with open(filename, "rb") as f:
            data = f.read()

        self.assertEqual(data, b"\x00\x01\x02\x03\x04")

        # clean up
        os.remove(filename)

    def test_no_leak(self):
        filename = tempfile.mktemp()

        # try opening and closing the file a bunch of times
        for _ in range(10000):
            with winunlock_open(filename, "w") as f:
                f.write(self.random_string(100))

        # if we got this far without an error, there was no handle leak

        # clean up
        os.remove(filename)

    def test_read_some_bytes(self):
        # create a temp file with some bytes
        filename = tempfile.mktemp()
        with open(filename, "wb") as f:
            f.write(b"\x00\x01\x02\x03\x04\x05\x06\x07\x08\x09")

        # try reading only some of the bytes with winunlock_open
        with winunlock_open(filename, "rb") as f:
            data = f.read(5)

        self.assertEqual(data, b"\x00\x01\x02\x03\x04")

        # clean up
        os.remove(filename)

    def test_seek_and_tell(self):
        # create a temp file with some bytes
        filename = tempfile.mktemp()
        with open(filename, "wb") as f:
            f.write(b"\x00\x01\x02\x03\x04\x05\x06\x07\x08\x09")

        # try seeking and reading with winunlock_open
        with winunlock_open(filename, "rb") as f:
            f.seek(5)
            data = f.read()

        self.assertEqual(data, b"\x05\x06\x07\x08\x09")

        # try seeking and telling with winunlock_open
        with winunlock_open(filename, "rb") as f:
            f.seek(5)
            position = f.tell()

        self.assertEqual(position, 5)

        # clean up
        os.remove(filename)

    def test_nonexistent_file(self):
        with self.assertRaises(FileNotFoundError):
            with winunlock_open("nonexistent_file.txt", "r") as f:
                pass

    def test_overwriting_content(self):
        filename = tempfile.mktemp()
        with winunlock_open(filename, "w") as f:
            f.write("hello world")
        with winunlock_open(filename, "w") as f:
            f.write("goodbye world")

        with open(filename, "r") as f:
            data = f.read()

        self.assertEqual(data, "goodbye world")

        # clean up
        os.remove(filename)

    def test_appending_content(self):
        filename = tempfile.mktemp()
        with winunlock_open(filename, "w") as f:
            f.write("hello world")
        with winunlock_open(filename, "a") as f:
            f.write(" and goodbye world")

        with open(filename, "r") as f:
            data = f.read()

        self.assertEqual(data, "hello world and goodbye world")

        # clean up
        os.remove(filename)

    def test_large_file(self):
        filename = tempfile.mktemp()
        content = "a" * (1024 * 1024 * 10)  # 10MB

        with winunlock_open(filename, "w") as f:
            f.write(content)

        with winunlock_open(filename, "r") as f:
            data = f.read()

        self.assertEqual(data, content)

        # clean up
        os.remove(filename)

    def test_invalid_parameters(self):
        with self.assertRaises(TypeError):
            with winunlock_open(1234, "r") as f:
                pass
        with self.assertRaises(ValueError):
            with winunlock_open(tempfile.mktemp(), "invalid_mode") as f:
                pass

    def test_read_few_bytes(self):
        # create a temp file with some bytes
        filename = tempfile.mktemp()
        content = "This is a sample string"
        with open(filename, "w") as f:
            f.write(content)

        # Open the file without 'with', read a few bytes, and close
        f = winunlock_open(filename, "r")
        data = f.read(4)  # reads the first 4 bytes/characters
        f.close()

        self.assertEqual(data, content[:4])  # compare with the first 4 characters

        # clean up
        os.remove(filename)


if __name__ == "__main__":
    unittest.main()
