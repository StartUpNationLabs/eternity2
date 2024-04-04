import {FC} from "react";
import {RotatedPiece} from "../proto/solver/v1/solver";
import Piece from "./Piece";
import {Hint} from "../utils/interface.tsx";

interface BoardProps {
    pieces?: RotatedPiece[];
    hints?: Hint[];
}

const Board: FC<BoardProps> = ({pieces, hints}: BoardProps) => {
    if (!pieces) {
        return <div>Empty board</div>;
    }
    const boardSize = Math.sqrt(pieces.length);

    return (
        <div>
            <div
                style={{
                    display: "grid",
                    gridTemplateColumns: `repeat(${boardSize}, 1fr)`,
                    gridTemplateRows: `repeat(${boardSize}, 1fr)`,
                }}
            >
                {pieces.map((rotatedPiece, index) => {
                    // Check if the current piece index is in the hints array
                    const isHint = hints?.some(hint => hint.index === index);

                    if (isHint) {
                        console.log(`Hint found at index ${index}`);
                    }

                    return (
                        <div style={{
                            // boxShadow: isHint ? 'inset 0 0 0 2px #000000' : undefined // Apply inner border if the piece is in the hint
                            border: isHint ? '8px solid #000000' : undefined // Apply inner border if the piece is in the hint
                        }}>
                            <Piece key={index} {...rotatedPiece}/>
                        </div>
                    );
                })}
            </div>
        </div>
    );
};

export default Board;
