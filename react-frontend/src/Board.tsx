import React, { useEffect, useState } from 'react';
import {createBoard, PieceData, rotatePiece, shuffleAndRotateBoard} from './logic';
import { SolverClient } from "./proto/solver/v1/solver.client";
import { GrpcWebFetchTransport } from "@protobuf-ts/grpcweb-transport";
import Piece from "./Piece.tsx";

interface BoardProps {
    size: number;
    numberOfSymbols: number;
}

const Board: React.FC<BoardProps> = ({ size, numberOfSymbols }) => {
    const [board, setBoard] = useState<PieceData[][]>([]);
    const [shuffledBoard, setShuffledBoard] = useState<PieceData[][]>([]);
    const [resolvedBoard, setResolvedBoard] = useState<PieceData[][]>([]); // New state for the resolved board

    useEffect(() => {
        const newBoard = createBoard(size, numberOfSymbols);
        setBoard(newBoard);
        setShuffledBoard([]);
        setResolvedBoard([]); // Reset resolvedBoard when size or numberOfSymbols changes
    }, [size, numberOfSymbols]);

    const shuffleAndDisplayBoard = () => {
        const shuffled = shuffleAndRotateBoard([...board]);
        setShuffledBoard(shuffled);
    };

    const resolveAndDisplayBoard = async () => {
        const transport = new GrpcWebFetchTransport({
            baseUrl: "http://vmpx15.polytech.hs.ozeliurs.com:50052",
            format: "binary",
        });
        const solverClient = new SolverClient(transport);

        // Convertir les bords de chaque pièce du format binaire au format décimal attendu par l'API
        // et remplacer '0' par '65535'
        const pieces = shuffledBoard.flat().map(({ top, right, bottom, left }) => ({
            top: top === "0".repeat(16) ? 65535 : parseInt(top, 2),
            right: right === "0".repeat(16) ? 65535 : parseInt(right, 2),
            bottom: bottom === "0".repeat(16) ? 65535 : parseInt(bottom, 2),
            left: left === "0".repeat(16) ? 65535 : parseInt(left, 2),
        }));

        const stream = solverClient.solveStepByStep({
            pieces: pieces,
            threads: 4,
            hashThreshold: 4,
            waitTime: 1,
        });

        for await (const message of stream.responses) {
            const resolvedPieces = message.rotatedPieces.map(({ piece, rotation }) => {
                let rotatedPiece = {
                    top: piece.top === 65535 ? "0000000000000000" : piece.top.toString(2).padStart(16, '0'),
                    right: piece.right === 65535 ? "0000000000000000" : piece.right.toString(2).padStart(16, '0'),
                    bottom: piece.bottom === 65535 ? "0000000000000000" : piece.bottom.toString(2).padStart(16, '0'),
                    left: piece.left === 65535 ? "0000000000000000" : piece.left.toString(2).padStart(16, '0'),
                };
                rotatedPiece = rotatePiece(rotatedPiece, rotation);

                return rotatedPiece;
            });

            setResolvedBoard(resolvedPieces.reduce((acc, curr, index) => {
                const row = Math.floor(index / size);
                if (!acc[row]) acc[row] = [];
                acc[row].push(curr);
                return acc;
            }, []));
        }
    };


    return (
        <div>
            <button onClick={shuffleAndDisplayBoard}>Shuffle and Display Board</button>
            {shuffledBoard.length > 0 && (
                <button onClick={resolveAndDisplayBoard}>Resolve and Display Board</button>
            )}
            <div>
                <div style={{ marginTop: '20px' }}>
                    <h2>Original Board</h2>
                    <div style={{ display: 'grid', gridTemplateColumns: `repeat(${size}, 1fr)`, gap: '5px' }}>
                        {board.flat().map((piece, index) => (
                            <Piece key={`original-${index}`} piece={piece} />
                        ))}
                    </div>
                </div>

                {shuffledBoard.length > 0 && (
                    <div style={{ marginTop: '20px' }}>
                        <h2>Shuffled Board</h2>
                        <div style={{ display: 'grid', gridTemplateColumns: `repeat(${size}, 1fr)`, gap: '5px' }}>
                            {shuffledBoard.flat().map((piece, index) => (
                                <Piece key={`shuffled-${index}`} piece={piece} />
                            ))}
                        </div>
                    </div>
                )}

                {resolvedBoard.length > 0 && (
                    <div style={{ marginTop: '20px' }}>
                        <h2>Resolved Board</h2>
                        <div style={{ display: 'grid', gridTemplateColumns: `repeat(${size}, 1fr)`, gap: '5px' }}>
                            {resolvedBoard.flat().map((piece, index) => (
                                <Piece key={`resolved-${index}`} piece={piece} />
                            ))}
                        </div>
                    </div>
                )}
            </div>

        </div>
    );
};

export default Board;
