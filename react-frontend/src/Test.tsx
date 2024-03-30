import React, {FC} from 'react';
import {RotatedPiece} from "./proto/solver/v1/solver.ts";
import Board from "./components/Board.tsx";


interface AppProps {
}

const rotatedPiece: RotatedPiece = {
    piece: {
        top: 0,
        right: 1,
        bottom: 2,
        left: 3
    },
    rotation: 0,
    index: 0
}

const gridSize = 2;
const rotatedPieces: RotatedPiece[] = Array.from({length: gridSize**2}, () => (rotatedPiece));

const Test: FC<AppProps> = () => {
    const percentage: number = 90;
    return (
        <div style={{
            display: 'flex',
            justifyContent: 'center',
            alignItems: 'center',
            height: '100vh',
            width: '100vw'
        }}>
            <div style={{width: `${percentage}%`, height: `${percentage}%`}}>
                <Board pieces={rotatedPieces}/>
            </div>
        </div>
    );
};

export default Test;
