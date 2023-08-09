from typing import Callable, Union, IO, Any, Iterator
import io
from ._open import open as winunlock_open
from contextlib import contextmanager
import builtins
from os import PathLike
from ._iotype import _IOType

builtins_open = builtins.open


def _open(
    file: Union[PathLike[str], str],
    mode: str = "r",
    buffering: int = -1,
    encoding: str | None = None,
    errors: str | None = None,
    newline: str | None = None,
    closefd: bool = True,
    opener: Callable[[str, int], int] | None = None,
) -> _IOType:
    """
    A helper function that tries Python's built-in open function first and
    falls back to winunlock's open function in case of a PermissionError.

    Args:
        file (str): The path to the file to be opened.
        mode (str, optional): Mode in which the file is opened. Defaults to 'r'.
        buffering (int, optional): Set the buffering policy. Defaults to -1.
        encoding (str, optional): The name of the encoding. Defaults to None.
        errors (str, optional): Specifies how encoding errors are to be handled. Defaults to None.
        newline (str, optional): How newlines mode works. Defaults to None.
        closefd (bool, optional): Close the underlying file descriptor. Defaults to True.
        opener (Callable[[str, int], int], optional): A custom opener. Defaults to None.

    Returns:
        io.TextIOWrapper | io.BufferedRandom | io.BufferedWriter | io.BufferedReader | io.FileIO:
            File object corresponding to the mode.

    """

    # Don't patch if we're not opening a file for reading
    if not "r" in str(mode):
        return builtins_open(
            file, mode, buffering, encoding, errors, newline, closefd, opener
        )

    else:
        try:
            return builtins_open(
                file, mode, buffering, encoding, errors, newline, closefd, opener
            )
        except PermissionError as e:
            try:
                return winunlock_open(
                    file, mode, buffering, encoding, errors, newline, closefd, opener
                )

            # If we can't open the file, raise the original exception instead of the
            # one from open_locked in order for the whole system to behave as if
            # open_locked never existed.
            except Exception as e:
                raise e


@contextmanager
def monkeypatch_open() -> Iterator[None]:
    """
    A context manager that temporarily replaces the built-in open function
    with a custom function that tries Python's built-in open function first and
    falls back to winunlock's open function in case of a PermissionError.

    This context manager is useful when you want to read files that might be
    locked, without modifying the rest of your code.

    Example:
        >>> with monkeypatch_open():
        >>>     with open("locked_file.txt", "r") as f:
        >>>         content = f.read()

    Note:
        The built-in open function will be restored upon exiting the context.

    """
    save_open = builtins.open
    builtins.open = _open  # type: ignore
    yield
    builtins.open = save_open
