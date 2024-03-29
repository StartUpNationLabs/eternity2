from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Iterable as _Iterable, Mapping as _Mapping, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class SolverSolveRequest(_message.Message):
    __slots__ = ("pieces", "threads", "hash_threshold", "wait_time", "use_cache", "cache_pull_interval")
    PIECES_FIELD_NUMBER: _ClassVar[int]
    THREADS_FIELD_NUMBER: _ClassVar[int]
    HASH_THRESHOLD_FIELD_NUMBER: _ClassVar[int]
    WAIT_TIME_FIELD_NUMBER: _ClassVar[int]
    USE_CACHE_FIELD_NUMBER: _ClassVar[int]
    CACHE_PULL_INTERVAL_FIELD_NUMBER: _ClassVar[int]
    pieces: _containers.RepeatedCompositeFieldContainer[Piece]
    threads: int
    hash_threshold: int
    wait_time: int
    use_cache: bool
    cache_pull_interval: int
    def __init__(self, pieces: _Optional[_Iterable[_Union[Piece, _Mapping]]] = ..., threads: _Optional[int] = ..., hash_threshold: _Optional[int] = ..., wait_time: _Optional[int] = ..., use_cache: bool = ..., cache_pull_interval: _Optional[int] = ...) -> None: ...

class Piece(_message.Message):
    __slots__ = ("top", "right", "bottom", "left")
    TOP_FIELD_NUMBER: _ClassVar[int]
    RIGHT_FIELD_NUMBER: _ClassVar[int]
    BOTTOM_FIELD_NUMBER: _ClassVar[int]
    LEFT_FIELD_NUMBER: _ClassVar[int]
    top: int
    right: int
    bottom: int
    left: int
    def __init__(self, top: _Optional[int] = ..., right: _Optional[int] = ..., bottom: _Optional[int] = ..., left: _Optional[int] = ...) -> None: ...

class PieceWithOptionalHint(_message.Message):
    __slots__ = ("piece", "x", "y")
    PIECE_FIELD_NUMBER: _ClassVar[int]
    X_FIELD_NUMBER: _ClassVar[int]
    Y_FIELD_NUMBER: _ClassVar[int]
    piece: Piece
    x: int
    y: int
    def __init__(self, piece: _Optional[_Union[Piece, _Mapping]] = ..., x: _Optional[int] = ..., y: _Optional[int] = ...) -> None: ...

class RotatedPiece(_message.Message):
    __slots__ = ("piece", "rotation", "index")
    PIECE_FIELD_NUMBER: _ClassVar[int]
    ROTATION_FIELD_NUMBER: _ClassVar[int]
    INDEX_FIELD_NUMBER: _ClassVar[int]
    piece: Piece
    rotation: int
    index: int
    def __init__(self, piece: _Optional[_Union[Piece, _Mapping]] = ..., rotation: _Optional[int] = ..., index: _Optional[int] = ...) -> None: ...

class SolverStepByStepResponse(_message.Message):
    __slots__ = ("rotated_pieces",)
    ROTATED_PIECES_FIELD_NUMBER: _ClassVar[int]
    rotated_pieces: _containers.RepeatedCompositeFieldContainer[RotatedPiece]
    def __init__(self, rotated_pieces: _Optional[_Iterable[_Union[RotatedPiece, _Mapping]]] = ...) -> None: ...

class SolverSolveResponse(_message.Message):
    __slots__ = ("time", "hashes_per_second", "hash_table_size", "boards_per_second", "boards_analyzed", "hash_table_hits", "rotated_pieces")
    TIME_FIELD_NUMBER: _ClassVar[int]
    HASHES_PER_SECOND_FIELD_NUMBER: _ClassVar[int]
    HASH_TABLE_SIZE_FIELD_NUMBER: _ClassVar[int]
    BOARDS_PER_SECOND_FIELD_NUMBER: _ClassVar[int]
    BOARDS_ANALYZED_FIELD_NUMBER: _ClassVar[int]
    HASH_TABLE_HITS_FIELD_NUMBER: _ClassVar[int]
    ROTATED_PIECES_FIELD_NUMBER: _ClassVar[int]
    time: float
    hashes_per_second: float
    hash_table_size: int
    boards_per_second: float
    boards_analyzed: int
    hash_table_hits: int
    rotated_pieces: _containers.RepeatedCompositeFieldContainer[RotatedPiece]
    def __init__(self, time: _Optional[float] = ..., hashes_per_second: _Optional[float] = ..., hash_table_size: _Optional[int] = ..., boards_per_second: _Optional[float] = ..., boards_analyzed: _Optional[int] = ..., hash_table_hits: _Optional[int] = ..., rotated_pieces: _Optional[_Iterable[_Union[RotatedPiece, _Mapping]]] = ...) -> None: ...
