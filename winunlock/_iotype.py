from typing import IO, Any, Union
import io

_IOType = Union[
    IO[Any],
    io.TextIOWrapper,
    io.BufferedRandom,
    io.BufferedWriter,
    io.BufferedReader,
    io.FileIO
]