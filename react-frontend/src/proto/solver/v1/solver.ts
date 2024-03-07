// @generated by protobuf-ts 2.9.3
// @generated from protobuf file "solver/v1/solver.proto" (package "solver.v1", syntax proto3)
// tslint:disable
import { ServiceType } from "@protobuf-ts/runtime-rpc";
import type { BinaryWriteOptions } from "@protobuf-ts/runtime";
import type { IBinaryWriter } from "@protobuf-ts/runtime";
import { WireType } from "@protobuf-ts/runtime";
import type { BinaryReadOptions } from "@protobuf-ts/runtime";
import type { IBinaryReader } from "@protobuf-ts/runtime";
import { UnknownFieldHandler } from "@protobuf-ts/runtime";
import type { PartialMessage } from "@protobuf-ts/runtime";
import { reflectionMergePartial } from "@protobuf-ts/runtime";
import { MessageType } from "@protobuf-ts/runtime";
/**
 * @generated from protobuf message solver.v1.SolverSolveRequest
 */
export interface SolverSolveRequest {
    /**
     * @generated from protobuf field: repeated solver.v1.Piece pieces = 1;
     */
    pieces: Piece[];
    /**
     * @generated from protobuf field: uint32 threads = 2;
     */
    threads: number;
    /**
     * @generated from protobuf field: uint32 hash_threshold = 3;
     */
    hashThreshold: number;
    /**
     * @generated from protobuf field: uint32 wait_time = 4;
     */
    waitTime: number;
}
/**
 * @generated from protobuf message solver.v1.Piece
 */
export interface Piece {
    /**
     * @generated from protobuf field: uint32 top = 1;
     */
    top: number;
    /**
     * @generated from protobuf field: uint32 right = 2;
     */
    right: number;
    /**
     * @generated from protobuf field: uint32 bottom = 3;
     */
    bottom: number;
    /**
     * @generated from protobuf field: uint32 left = 4;
     */
    left: number;
}
/**
 * @generated from protobuf message solver.v1.PieceWithOptionalHint
 */
export interface PieceWithOptionalHint {
    /**
     * @generated from protobuf field: solver.v1.Piece piece = 1;
     */
    piece?: Piece;
    /**
     * @generated from protobuf field: optional int32 x = 2;
     */
    x?: number;
    /**
     * @generated from protobuf field: optional int32 y = 3;
     */
    y?: number;
}
/**
 * @generated from protobuf message solver.v1.RotatedPiece
 */
export interface RotatedPiece {
    /**
     * @generated from protobuf field: solver.v1.Piece piece = 1;
     */
    piece?: Piece;
    /**
     * @generated from protobuf field: uint32 rotation = 2;
     */
    rotation: number;
    /**
     * @generated from protobuf field: uint32 index = 3;
     */
    index: number;
}
/**
 * @generated from protobuf message solver.v1.SolverStepByStepResponse
 */
export interface SolverStepByStepResponse {
    /**
     * @generated from protobuf field: repeated solver.v1.RotatedPiece rotated_pieces = 1;
     */
    rotatedPieces: RotatedPiece[];
}
/**
 * @generated from protobuf message solver.v1.SolverSolveResponse
 */
export interface SolverSolveResponse {
    /**
     * @generated from protobuf field: double time = 1;
     */
    time: number;
    /**
     * @generated from protobuf field: double hashes_per_second = 2;
     */
    hashesPerSecond: number;
    /**
     * @generated from protobuf field: uint32 hash_table_size = 3;
     */
    hashTableSize: number;
    /**
     * @generated from protobuf field: double boards_per_second = 4;
     */
    boardsPerSecond: number;
    /**
     * @generated from protobuf field: uint32 boards_analyzed = 5;
     */
    boardsAnalyzed: number;
    /**
     * @generated from protobuf field: uint32 hash_table_hits = 6;
     */
    hashTableHits: number;
    /**
     * @generated from protobuf field: repeated solver.v1.RotatedPiece rotated_pieces = 7;
     */
    rotatedPieces: RotatedPiece[];
}
// @generated message type with reflection information, may provide speed optimized methods
class SolverSolveRequest$Type extends MessageType<SolverSolveRequest> {
    constructor() {
        super("solver.v1.SolverSolveRequest", [
            { no: 1, name: "pieces", kind: "message", repeat: 1 /*RepeatType.PACKED*/, T: () => Piece },
            { no: 2, name: "threads", kind: "scalar", T: 13 /*ScalarType.UINT32*/ },
            { no: 3, name: "hash_threshold", kind: "scalar", T: 13 /*ScalarType.UINT32*/ },
            { no: 4, name: "wait_time", kind: "scalar", T: 13 /*ScalarType.UINT32*/ }
        ]);
    }
    create(value?: PartialMessage<SolverSolveRequest>): SolverSolveRequest {
        const message = globalThis.Object.create((this.messagePrototype!));
        message.pieces = [];
        message.threads = 0;
        message.hashThreshold = 0;
        message.waitTime = 0;
        if (value !== undefined)
            reflectionMergePartial<SolverSolveRequest>(this, message, value);
        return message;
    }
    internalBinaryRead(reader: IBinaryReader, length: number, options: BinaryReadOptions, target?: SolverSolveRequest): SolverSolveRequest {
        let message = target ?? this.create(), end = reader.pos + length;
        while (reader.pos < end) {
            let [fieldNo, wireType] = reader.tag();
            switch (fieldNo) {
                case /* repeated solver.v1.Piece pieces */ 1:
                    message.pieces.push(Piece.internalBinaryRead(reader, reader.uint32(), options));
                    break;
                case /* uint32 threads */ 2:
                    message.threads = reader.uint32();
                    break;
                case /* uint32 hash_threshold */ 3:
                    message.hashThreshold = reader.uint32();
                    break;
                case /* uint32 wait_time */ 4:
                    message.waitTime = reader.uint32();
                    break;
                default:
                    let u = options.readUnknownField;
                    if (u === "throw")
                        throw new globalThis.Error(`Unknown field ${fieldNo} (wire type ${wireType}) for ${this.typeName}`);
                    let d = reader.skip(wireType);
                    if (u !== false)
                        (u === true ? UnknownFieldHandler.onRead : u)(this.typeName, message, fieldNo, wireType, d);
            }
        }
        return message;
    }
    internalBinaryWrite(message: SolverSolveRequest, writer: IBinaryWriter, options: BinaryWriteOptions): IBinaryWriter {
        /* repeated solver.v1.Piece pieces = 1; */
        for (let i = 0; i < message.pieces.length; i++)
            Piece.internalBinaryWrite(message.pieces[i], writer.tag(1, WireType.LengthDelimited).fork(), options).join();
        /* uint32 threads = 2; */
        if (message.threads !== 0)
            writer.tag(2, WireType.Varint).uint32(message.threads);
        /* uint32 hash_threshold = 3; */
        if (message.hashThreshold !== 0)
            writer.tag(3, WireType.Varint).uint32(message.hashThreshold);
        /* uint32 wait_time = 4; */
        if (message.waitTime !== 0)
            writer.tag(4, WireType.Varint).uint32(message.waitTime);
        let u = options.writeUnknownFields;
        if (u !== false)
            (u == true ? UnknownFieldHandler.onWrite : u)(this.typeName, message, writer);
        return writer;
    }
}
/**
 * @generated MessageType for protobuf message solver.v1.SolverSolveRequest
 */
export const SolverSolveRequest = new SolverSolveRequest$Type();
// @generated message type with reflection information, may provide speed optimized methods
class Piece$Type extends MessageType<Piece> {
    constructor() {
        super("solver.v1.Piece", [
            { no: 1, name: "top", kind: "scalar", T: 13 /*ScalarType.UINT32*/ },
            { no: 2, name: "right", kind: "scalar", T: 13 /*ScalarType.UINT32*/ },
            { no: 3, name: "bottom", kind: "scalar", T: 13 /*ScalarType.UINT32*/ },
            { no: 4, name: "left", kind: "scalar", T: 13 /*ScalarType.UINT32*/ }
        ]);
    }
    create(value?: PartialMessage<Piece>): Piece {
        const message = globalThis.Object.create((this.messagePrototype!));
        message.top = 0;
        message.right = 0;
        message.bottom = 0;
        message.left = 0;
        if (value !== undefined)
            reflectionMergePartial<Piece>(this, message, value);
        return message;
    }
    internalBinaryRead(reader: IBinaryReader, length: number, options: BinaryReadOptions, target?: Piece): Piece {
        let message = target ?? this.create(), end = reader.pos + length;
        while (reader.pos < end) {
            let [fieldNo, wireType] = reader.tag();
            switch (fieldNo) {
                case /* uint32 top */ 1:
                    message.top = reader.uint32();
                    break;
                case /* uint32 right */ 2:
                    message.right = reader.uint32();
                    break;
                case /* uint32 bottom */ 3:
                    message.bottom = reader.uint32();
                    break;
                case /* uint32 left */ 4:
                    message.left = reader.uint32();
                    break;
                default:
                    let u = options.readUnknownField;
                    if (u === "throw")
                        throw new globalThis.Error(`Unknown field ${fieldNo} (wire type ${wireType}) for ${this.typeName}`);
                    let d = reader.skip(wireType);
                    if (u !== false)
                        (u === true ? UnknownFieldHandler.onRead : u)(this.typeName, message, fieldNo, wireType, d);
            }
        }
        return message;
    }
    internalBinaryWrite(message: Piece, writer: IBinaryWriter, options: BinaryWriteOptions): IBinaryWriter {
        /* uint32 top = 1; */
        if (message.top !== 0)
            writer.tag(1, WireType.Varint).uint32(message.top);
        /* uint32 right = 2; */
        if (message.right !== 0)
            writer.tag(2, WireType.Varint).uint32(message.right);
        /* uint32 bottom = 3; */
        if (message.bottom !== 0)
            writer.tag(3, WireType.Varint).uint32(message.bottom);
        /* uint32 left = 4; */
        if (message.left !== 0)
            writer.tag(4, WireType.Varint).uint32(message.left);
        let u = options.writeUnknownFields;
        if (u !== false)
            (u == true ? UnknownFieldHandler.onWrite : u)(this.typeName, message, writer);
        return writer;
    }
}
/**
 * @generated MessageType for protobuf message solver.v1.Piece
 */
export const Piece = new Piece$Type();
// @generated message type with reflection information, may provide speed optimized methods
class PieceWithOptionalHint$Type extends MessageType<PieceWithOptionalHint> {
    constructor() {
        super("solver.v1.PieceWithOptionalHint", [
            { no: 1, name: "piece", kind: "message", T: () => Piece },
            { no: 2, name: "x", kind: "scalar", opt: true, T: 5 /*ScalarType.INT32*/ },
            { no: 3, name: "y", kind: "scalar", opt: true, T: 5 /*ScalarType.INT32*/ }
        ]);
    }
    create(value?: PartialMessage<PieceWithOptionalHint>): PieceWithOptionalHint {
        const message = globalThis.Object.create((this.messagePrototype!));
        if (value !== undefined)
            reflectionMergePartial<PieceWithOptionalHint>(this, message, value);
        return message;
    }
    internalBinaryRead(reader: IBinaryReader, length: number, options: BinaryReadOptions, target?: PieceWithOptionalHint): PieceWithOptionalHint {
        let message = target ?? this.create(), end = reader.pos + length;
        while (reader.pos < end) {
            let [fieldNo, wireType] = reader.tag();
            switch (fieldNo) {
                case /* solver.v1.Piece piece */ 1:
                    message.piece = Piece.internalBinaryRead(reader, reader.uint32(), options, message.piece);
                    break;
                case /* optional int32 x */ 2:
                    message.x = reader.int32();
                    break;
                case /* optional int32 y */ 3:
                    message.y = reader.int32();
                    break;
                default:
                    let u = options.readUnknownField;
                    if (u === "throw")
                        throw new globalThis.Error(`Unknown field ${fieldNo} (wire type ${wireType}) for ${this.typeName}`);
                    let d = reader.skip(wireType);
                    if (u !== false)
                        (u === true ? UnknownFieldHandler.onRead : u)(this.typeName, message, fieldNo, wireType, d);
            }
        }
        return message;
    }
    internalBinaryWrite(message: PieceWithOptionalHint, writer: IBinaryWriter, options: BinaryWriteOptions): IBinaryWriter {
        /* solver.v1.Piece piece = 1; */
        if (message.piece)
            Piece.internalBinaryWrite(message.piece, writer.tag(1, WireType.LengthDelimited).fork(), options).join();
        /* optional int32 x = 2; */
        if (message.x !== undefined)
            writer.tag(2, WireType.Varint).int32(message.x);
        /* optional int32 y = 3; */
        if (message.y !== undefined)
            writer.tag(3, WireType.Varint).int32(message.y);
        let u = options.writeUnknownFields;
        if (u !== false)
            (u == true ? UnknownFieldHandler.onWrite : u)(this.typeName, message, writer);
        return writer;
    }
}
/**
 * @generated MessageType for protobuf message solver.v1.PieceWithOptionalHint
 */
export const PieceWithOptionalHint = new PieceWithOptionalHint$Type();
// @generated message type with reflection information, may provide speed optimized methods
class RotatedPiece$Type extends MessageType<RotatedPiece> {
    constructor() {
        super("solver.v1.RotatedPiece", [
            { no: 1, name: "piece", kind: "message", T: () => Piece },
            { no: 2, name: "rotation", kind: "scalar", T: 13 /*ScalarType.UINT32*/ },
            { no: 3, name: "index", kind: "scalar", T: 13 /*ScalarType.UINT32*/ }
        ]);
    }
    create(value?: PartialMessage<RotatedPiece>): RotatedPiece {
        const message = globalThis.Object.create((this.messagePrototype!));
        message.rotation = 0;
        message.index = 0;
        if (value !== undefined)
            reflectionMergePartial<RotatedPiece>(this, message, value);
        return message;
    }
    internalBinaryRead(reader: IBinaryReader, length: number, options: BinaryReadOptions, target?: RotatedPiece): RotatedPiece {
        let message = target ?? this.create(), end = reader.pos + length;
        while (reader.pos < end) {
            let [fieldNo, wireType] = reader.tag();
            switch (fieldNo) {
                case /* solver.v1.Piece piece */ 1:
                    message.piece = Piece.internalBinaryRead(reader, reader.uint32(), options, message.piece);
                    break;
                case /* uint32 rotation */ 2:
                    message.rotation = reader.uint32();
                    break;
                case /* uint32 index */ 3:
                    message.index = reader.uint32();
                    break;
                default:
                    let u = options.readUnknownField;
                    if (u === "throw")
                        throw new globalThis.Error(`Unknown field ${fieldNo} (wire type ${wireType}) for ${this.typeName}`);
                    let d = reader.skip(wireType);
                    if (u !== false)
                        (u === true ? UnknownFieldHandler.onRead : u)(this.typeName, message, fieldNo, wireType, d);
            }
        }
        return message;
    }
    internalBinaryWrite(message: RotatedPiece, writer: IBinaryWriter, options: BinaryWriteOptions): IBinaryWriter {
        /* solver.v1.Piece piece = 1; */
        if (message.piece)
            Piece.internalBinaryWrite(message.piece, writer.tag(1, WireType.LengthDelimited).fork(), options).join();
        /* uint32 rotation = 2; */
        if (message.rotation !== 0)
            writer.tag(2, WireType.Varint).uint32(message.rotation);
        /* uint32 index = 3; */
        if (message.index !== 0)
            writer.tag(3, WireType.Varint).uint32(message.index);
        let u = options.writeUnknownFields;
        if (u !== false)
            (u == true ? UnknownFieldHandler.onWrite : u)(this.typeName, message, writer);
        return writer;
    }
}
/**
 * @generated MessageType for protobuf message solver.v1.RotatedPiece
 */
export const RotatedPiece = new RotatedPiece$Type();
// @generated message type with reflection information, may provide speed optimized methods
class SolverStepByStepResponse$Type extends MessageType<SolverStepByStepResponse> {
    constructor() {
        super("solver.v1.SolverStepByStepResponse", [
            { no: 1, name: "rotated_pieces", kind: "message", repeat: 1 /*RepeatType.PACKED*/, T: () => RotatedPiece }
        ]);
    }
    create(value?: PartialMessage<SolverStepByStepResponse>): SolverStepByStepResponse {
        const message = globalThis.Object.create((this.messagePrototype!));
        message.rotatedPieces = [];
        if (value !== undefined)
            reflectionMergePartial<SolverStepByStepResponse>(this, message, value);
        return message;
    }
    internalBinaryRead(reader: IBinaryReader, length: number, options: BinaryReadOptions, target?: SolverStepByStepResponse): SolverStepByStepResponse {
        let message = target ?? this.create(), end = reader.pos + length;
        while (reader.pos < end) {
            let [fieldNo, wireType] = reader.tag();
            switch (fieldNo) {
                case /* repeated solver.v1.RotatedPiece rotated_pieces */ 1:
                    message.rotatedPieces.push(RotatedPiece.internalBinaryRead(reader, reader.uint32(), options));
                    break;
                default:
                    let u = options.readUnknownField;
                    if (u === "throw")
                        throw new globalThis.Error(`Unknown field ${fieldNo} (wire type ${wireType}) for ${this.typeName}`);
                    let d = reader.skip(wireType);
                    if (u !== false)
                        (u === true ? UnknownFieldHandler.onRead : u)(this.typeName, message, fieldNo, wireType, d);
            }
        }
        return message;
    }
    internalBinaryWrite(message: SolverStepByStepResponse, writer: IBinaryWriter, options: BinaryWriteOptions): IBinaryWriter {
        /* repeated solver.v1.RotatedPiece rotated_pieces = 1; */
        for (let i = 0; i < message.rotatedPieces.length; i++)
            RotatedPiece.internalBinaryWrite(message.rotatedPieces[i], writer.tag(1, WireType.LengthDelimited).fork(), options).join();
        let u = options.writeUnknownFields;
        if (u !== false)
            (u == true ? UnknownFieldHandler.onWrite : u)(this.typeName, message, writer);
        return writer;
    }
}
/**
 * @generated MessageType for protobuf message solver.v1.SolverStepByStepResponse
 */
export const SolverStepByStepResponse = new SolverStepByStepResponse$Type();
// @generated message type with reflection information, may provide speed optimized methods
class SolverSolveResponse$Type extends MessageType<SolverSolveResponse> {
    constructor() {
        super("solver.v1.SolverSolveResponse", [
            { no: 1, name: "time", kind: "scalar", T: 1 /*ScalarType.DOUBLE*/ },
            { no: 2, name: "hashes_per_second", kind: "scalar", T: 1 /*ScalarType.DOUBLE*/ },
            { no: 3, name: "hash_table_size", kind: "scalar", T: 13 /*ScalarType.UINT32*/ },
            { no: 4, name: "boards_per_second", kind: "scalar", T: 1 /*ScalarType.DOUBLE*/ },
            { no: 5, name: "boards_analyzed", kind: "scalar", T: 13 /*ScalarType.UINT32*/ },
            { no: 6, name: "hash_table_hits", kind: "scalar", T: 13 /*ScalarType.UINT32*/ },
            { no: 7, name: "rotated_pieces", kind: "message", repeat: 1 /*RepeatType.PACKED*/, T: () => RotatedPiece }
        ]);
    }
    create(value?: PartialMessage<SolverSolveResponse>): SolverSolveResponse {
        const message = globalThis.Object.create((this.messagePrototype!));
        message.time = 0;
        message.hashesPerSecond = 0;
        message.hashTableSize = 0;
        message.boardsPerSecond = 0;
        message.boardsAnalyzed = 0;
        message.hashTableHits = 0;
        message.rotatedPieces = [];
        if (value !== undefined)
            reflectionMergePartial<SolverSolveResponse>(this, message, value);
        return message;
    }
    internalBinaryRead(reader: IBinaryReader, length: number, options: BinaryReadOptions, target?: SolverSolveResponse): SolverSolveResponse {
        let message = target ?? this.create(), end = reader.pos + length;
        while (reader.pos < end) {
            let [fieldNo, wireType] = reader.tag();
            switch (fieldNo) {
                case /* double time */ 1:
                    message.time = reader.double();
                    break;
                case /* double hashes_per_second */ 2:
                    message.hashesPerSecond = reader.double();
                    break;
                case /* uint32 hash_table_size */ 3:
                    message.hashTableSize = reader.uint32();
                    break;
                case /* double boards_per_second */ 4:
                    message.boardsPerSecond = reader.double();
                    break;
                case /* uint32 boards_analyzed */ 5:
                    message.boardsAnalyzed = reader.uint32();
                    break;
                case /* uint32 hash_table_hits */ 6:
                    message.hashTableHits = reader.uint32();
                    break;
                case /* repeated solver.v1.RotatedPiece rotated_pieces */ 7:
                    message.rotatedPieces.push(RotatedPiece.internalBinaryRead(reader, reader.uint32(), options));
                    break;
                default:
                    let u = options.readUnknownField;
                    if (u === "throw")
                        throw new globalThis.Error(`Unknown field ${fieldNo} (wire type ${wireType}) for ${this.typeName}`);
                    let d = reader.skip(wireType);
                    if (u !== false)
                        (u === true ? UnknownFieldHandler.onRead : u)(this.typeName, message, fieldNo, wireType, d);
            }
        }
        return message;
    }
    internalBinaryWrite(message: SolverSolveResponse, writer: IBinaryWriter, options: BinaryWriteOptions): IBinaryWriter {
        /* double time = 1; */
        if (message.time !== 0)
            writer.tag(1, WireType.Bit64).double(message.time);
        /* double hashes_per_second = 2; */
        if (message.hashesPerSecond !== 0)
            writer.tag(2, WireType.Bit64).double(message.hashesPerSecond);
        /* uint32 hash_table_size = 3; */
        if (message.hashTableSize !== 0)
            writer.tag(3, WireType.Varint).uint32(message.hashTableSize);
        /* double boards_per_second = 4; */
        if (message.boardsPerSecond !== 0)
            writer.tag(4, WireType.Bit64).double(message.boardsPerSecond);
        /* uint32 boards_analyzed = 5; */
        if (message.boardsAnalyzed !== 0)
            writer.tag(5, WireType.Varint).uint32(message.boardsAnalyzed);
        /* uint32 hash_table_hits = 6; */
        if (message.hashTableHits !== 0)
            writer.tag(6, WireType.Varint).uint32(message.hashTableHits);
        /* repeated solver.v1.RotatedPiece rotated_pieces = 7; */
        for (let i = 0; i < message.rotatedPieces.length; i++)
            RotatedPiece.internalBinaryWrite(message.rotatedPieces[i], writer.tag(7, WireType.LengthDelimited).fork(), options).join();
        let u = options.writeUnknownFields;
        if (u !== false)
            (u == true ? UnknownFieldHandler.onWrite : u)(this.typeName, message, writer);
        return writer;
    }
}
/**
 * @generated MessageType for protobuf message solver.v1.SolverSolveResponse
 */
export const SolverSolveResponse = new SolverSolveResponse$Type();
/**
 * @generated ServiceType for protobuf service solver.v1.Solver
 */
export const Solver = new ServiceType("solver.v1.Solver", [
    { name: "Solve", serverStreaming: true, options: {}, I: SolverSolveRequest, O: SolverSolveResponse },
    { name: "SolveStepByStep", serverStreaming: true, options: {}, I: SolverSolveRequest, O: SolverStepByStepResponse }
]);
