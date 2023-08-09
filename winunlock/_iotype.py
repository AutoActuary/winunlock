from typing import IO, Any, Union
import io

_IOType = (
    IO[Any]
    | io.TextIOWrapper
    | io.BufferedRandom
    | io.BufferedWriter
    | io.BufferedReader
    | io.FileIO
)
