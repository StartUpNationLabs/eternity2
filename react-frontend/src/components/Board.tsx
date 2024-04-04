import {FC} from "react";
import {Hint, RotatedPiece} from "../proto/solver/v1/solver";
import Piece from "./Piece";

interface BoardProps {
    pieces?: RotatedPiece[];
    hints?: Hint[];
}

const Board: FC<BoardProps> = (props: BoardProps) => {
    if (!props.pieces) {
        return <div>Empty board</div>;
    }
    const boardSize = Math.sqrt(props.pieces.length);

    return (
        <div>
            <div
                style={{
                    display: "grid",
                    gridTemplateColumns: `repeat(${boardSize}, 1fr)`,
                    gridTemplateRows: `repeat(${boardSize}, 1fr)`,
                }}
            >
                {props.pieces.map((rotatedPiece, index) => {
                    // Convert index to x, y
                    const x = index % boardSize;
                    const y = Math.floor(index / boardSize);

                    // Check if the current piece index is in the hints array
                    const isHint = props.hints?.some(hint => hint.x === x && hint.y === y);

                    return (
                        <div style={{
                            // Apply inner border if the piece is in the hint
                            border: isHint ? '6px solid #000000' : undefined
                        }}
                             key={index}
                        >
                            <Piece key={index} {...rotatedPiece}/>
                        </div>
                    );
                })}
            </div>
        </div>
    );
};

export default Board;
