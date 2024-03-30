import React, {FC} from 'react';
import ResponsiveAppBar from "./components/ResponsiveAppBar.tsx";
import Piece from "./components/Piece.tsx";
import {RotatedPiece} from "./proto/solver/v1/solver.ts";


interface AppProps {
}

const rotatedPiece: RotatedPiece = {
    piece: {
        top: 0,
        right: 8,
        bottom: 10,
        left: 3
    },
    rotation: 0,
    index: 0
}

const App: FC<AppProps> = () => (
        <div>
            <ResponsiveAppBar/>
            <Piece {...rotatedPiece}/>
        </div>
    )
;

export default App;
