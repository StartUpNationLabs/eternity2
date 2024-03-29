import React from 'react';

interface PieceProps {
    piece: {
        top: string;
        right: string;
        bottom: string;
        left: string;
    };
}

const Piece: React.FC<PieceProps> = ({ piece }) => {
    const topDecimal = parseInt(piece.top, 2);
    const rightDecimal = parseInt(piece.right, 2);
    const bottomDecimal = parseInt(piece.bottom, 2);
    const leftDecimal = parseInt(piece.left, 2);

    return (
        <div style={{ width: '50px', height: '50px', display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'center', border: '1px solid black' }}>
            <div>{topDecimal}</div>
            <div style={{ display: 'flex', justifyContent: 'space-between', width: '100%' }}>
                <span>{leftDecimal}</span>
                <span>{rightDecimal}</span>
            </div>
            <div>{bottomDecimal}</div>
        </div>
    );
}

export default Piece;
