import { FC, useState, useRef, useEffect } from "react";
import { Box } from "@mui/material";
import { RotatedPiece } from "../../proto/solver/v1/solver.ts";
import Piece from "../../components/Piece.tsx";

// Define drag data type
interface DragData {
    type: 'piece';
    pieceIndex: number;
    rotation: number;
}

interface DraggablePieceProps {
    piece: RotatedPiece;
    isDraggable?: boolean;
    rotation?: number;
    onRotate?: (rotation: number) => void;
    onClick?: () => void;
}

// Board drop zone component
interface BoardDropZoneProps {
    gridSize: number;
    board: (RotatedPiece | null)[];
    onDrop: (pieceIndex: number, boardIndex: number, rotation: number) => void;
    onRotate?: (pieceIndex: number, rotation: number) => void;
    onRemove?: (boardIndex: number) => void;
}

const BoardDropZone: FC<BoardDropZoneProps> = ({ gridSize, board, onDrop, onRotate, onRemove }) => {
    // Handle piece rotation on the board
    const handleRotate = (index: number, rotation: number) => {
        if (onRotate) {
            onRotate(index, rotation);
        }
    };
    
    // Handle piece removal from the board
    const handleRemove = (index: number) => {
        if (onRemove) {
            onRemove(index);
        }
    };
    
    // Handle drop on a cell
    const handleDrop = (index: number) => (e: React.DragEvent) => {
        e.preventDefault();
        
        try {
            const data = JSON.parse(e.dataTransfer.getData("application/json")) as DragData;
            if (data.type === 'piece') {
                onDrop(data.pieceIndex, index, data.rotation);
            }
        } catch (err) {
            console.error("Error parsing drag data:", err);
        }
    };
    
    // Handle drag over to allow drop
    const handleDragOver = (e: React.DragEvent) => {
        e.preventDefault();
    };

    return (
        <div style={{
            display: "grid",
            gridTemplateColumns: `repeat(${gridSize}, 1fr)`,
            gridTemplateRows: `repeat(${gridSize}, 1fr)`,
            width: '100%',
            height: '100%',
        }}>
            {board.map((cellPiece, index) => (
                <div 
                    key={index}
                    style={{
                        border: '1px solid #000',
                        background: cellPiece ? 'transparent' : '#f5f5f5',
                    }}
                    onDrop={handleDrop(index)}
                    onDragOver={handleDragOver}
                >
                    {cellPiece && (
                        <DraggablePiece 
                            piece={cellPiece.piece ? cellPiece : { ...cellPiece, piece: cellPiece.piece }} 
                            rotation={cellPiece.rotation}
                            onRotate={(rotation) => handleRotate(index, rotation)}
                            onClick={() => handleRemove(index)}
                        />
                    )}
                </div>
            ))}
        </div>
    );
};

const DraggablePieceBase: FC<DraggablePieceProps> = ({ 
    piece, 
    isDraggable = false,
    rotation,
    onRotate,
    onClick
}) => {
    const [currentRotation, setCurrentRotation] = useState(rotation !== undefined ? rotation : piece.rotation);
    const pieceRef = useRef<HTMLDivElement>(null);

    // Update rotation when prop changes
    useEffect(() => {
        if (rotation !== undefined) {
            setCurrentRotation(rotation);
        }
    }, [rotation]);

    // Handle right-click to rotate
    const handleRightClick = (e: React.MouseEvent) => {
        e.preventDefault();
        const newRotation = (currentRotation + 1) % 4;
        setCurrentRotation(newRotation);
        
        // Notify parent if onRotate callback exists
        if (onRotate) {
            onRotate(newRotation);
        }
    };
    
    // Handle click to potentially remove piece
    const handleClick = (_: React.MouseEvent) => {
        if (onClick) {
            onClick();
        }
    };
    
    // Handle drag start
    const handleDragStart = (e: React.DragEvent) => {
        if (!isDraggable) return;
        
        // Set drag data
        const dragData: DragData = {
            type: 'piece',
            pieceIndex: piece.index,
            rotation: currentRotation
        };
        
        e.dataTransfer.setData("application/json", JSON.stringify(dragData));
        
        // Set drag image
        if (pieceRef.current) {
            // Create a clone of the element for the drag image
            const rect = pieceRef.current.getBoundingClientRect();
            e.dataTransfer.setDragImage(pieceRef.current, rect.width / 2, rect.height / 2);
        }
    };
    
    // Create a piece with the current rotation
    const rotatedPiece: RotatedPiece = {
        ...piece,
        rotation: currentRotation
    };

    return (
        <Box 
            ref={pieceRef}
            draggable={isDraggable}
            onDragStart={handleDragStart}
            onContextMenu={handleRightClick}
            onClick={handleClick}
            sx={{ 
                width: '100%', 
                height: '100%',
                cursor: isDraggable ? 'grab' : 'pointer',
                '&:active': {
                    cursor: isDraggable ? 'grabbing' : 'pointer',
                },
                position: 'relative',
                '&:hover': onClick ? {
                    '&::after': {
                        content: '""',
                        position: 'absolute',
                        top: 0,
                        left: 0,
                        right: 0,
                        bottom: 0,
                        backgroundColor: 'rgba(0, 0, 0, 0.1)',
                        zIndex: 1,
                        borderRadius: '4px',
                    }
                } : {},
            }}
        >
            <Piece {...rotatedPiece} />
        </Box>
    );
};

const DraggablePiece = DraggablePieceBase as typeof DraggablePieceBase & {
    BoardDropZone: typeof BoardDropZone;
};

DraggablePiece.BoardDropZone = BoardDropZone;

export default DraggablePiece; 