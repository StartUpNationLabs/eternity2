import {FC} from "react";
import {RotatedPiece} from "../proto/solver/v1/solver";
import Piece from "./Piece";

interface BoardProps {
    pieces?: RotatedPiece[];
}

const Board: FC<BoardProps> = ({pieces}: BoardProps) => {
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
                {pieces.map((rotatedPiece, index) => (
                    <Piece key={index} {...rotatedPiece} />
                ))}
            </div>
        </div>
    );
};

export default Board;
