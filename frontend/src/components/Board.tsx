import {FC} from "react";
import {Hint, RotatedPiece} from "../proto/solver/v1/solver";
import Piece from "./Piece";

interface BoardProps {
    pieces?: RotatedPiece[];
    hints?: Hint[];
    showCuttingGuide?: boolean;
}

const Board: FC<BoardProps> = (props: BoardProps) => {
    if (!props.pieces) {
        return <div>Empty board</div>;
    }
    const boardSize = Math.sqrt(props.pieces.length);

    return (
        <div style={{
            width: "100%",
            aspectRatio: 1,
            lineHeight: 0,
            backgroundColor: "#808080",
        }}>
            <div
                style={{
                    display: "grid",
                    gridTemplateColumns: `repeat(${boardSize}, minmax(0, 1fr))`,
                    gridTemplateRows: `repeat(${boardSize}, minmax(0, 1fr))`,
                    gap: 0,
                    width: "100%",
                    height: "100%",
                    fontSize: 0,
                    lineHeight: 0,
                }}
            >
                {props.pieces.map((rotatedPiece, index) => {
                    const x = index % boardSize;
                    const y = Math.floor(index / boardSize);
                    const isHint = props.hints?.some(hint => hint.x === x && hint.y === y);

                    return (
                        <div style={{
                            border: props.showCuttingGuide ? '2px solid #000' : (isHint ? '6px solid #000000' : undefined),
                            boxSizing: 'border-box',
                            width: "100%",
                            height: "100%",
                            padding: 0,
                            margin: 0,
                            overflow: "hidden",
                            fontSize: 0,
                            lineHeight: 0,
                            display: "flex",
                            alignItems: "center",
                            justifyContent: "center",
                            position: "relative",
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
