# winunlock

`winunlock` is a Windows Python module that provides functionality for opening certain types of locked files in Windows, especially the ones that are usually inaccessible due to external locks (e.g. an Excel file being locked by OneDrive). The module exposes two utilities:
-  `winunlock.open` mimics Python's built-in `open` but is capable of accessing locked files, and
-  `winunlock.monkeypatch_open` are used to monkey patch Python's built-in `open` to allow reading locked files.

### Installation

```bash
pip install winunlock
```

### Usage

#### Basic open:

```python
import winunlock

# winunlock.open has the same interface as open
with winunlock.open("locked_file_path.txt", "r") as f:
    content = f.read()
```

#### Monkey patching:

```python
from winunlock import monkeypatch_open
import pandas as pd

with monkeypatch_open():
    # open has been temporarily patched
    with open("locked_file_path.txt", "r") as f:
        content = f.read()

    # external code can now read locked files by default
    pd.load_csv("locked_file_path.txt")
```

### Testing

The testing framework used is `unittest`. The tests are currently **dependent on a working Excel installation**. You can run the tests by executing the provided test script:

```bash
python tests.py
```

In order to test full compatibility with Python's `open`, more tests are needed.

### Limitations

While `winunlock` is designed to handle locked files gracefully, there are certain intense locks (as demonstrated in one of the tests) that it might still not be able to handle.

### Contributing

Contributions to improve `winunlock` or expand its functionalities are welcome. Please ensure that you include unit tests for any new features or changes.

### License

[Specify your license here, e.g., MIT, Apache, etc.]

* * *

## Documentation

### winunlock.open

```python
def open(file, mode='r', buffering=-1, encoding=None, errors=None, newline=None, closefd=True, opener=None):
    pass
```

This function is a drop-in replacement for Python's built-in open, designed to work with locked files.

**Parameters:**

* All parameters are the same as the built-in open.

### winunlock.monkeypatch_open

```python
@contextlib.contextmanager
def monkeypatch_open():
    pass
```

This context manager monkey patch Python's built-in `open` function in order to try to open a file via `winunlock.open` after `open` throws a `PermissionError`. After using the context manager, the built-in open will return to its normal functionality once out of the context.

