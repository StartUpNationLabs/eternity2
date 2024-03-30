import React from "react";
import {Direction, ETERNITY_PATTERNS} from "../utils/Constants.tsx";
import {RotatedPiece} from "../helper/proto/solver/v1/solver.ts";

const Piece = (props: RotatedPiece) => {
    // Get the corresponding eternity pattern from the constants
    const topPattern = ETERNITY_PATTERNS.find(pattern => pattern.binaryInt === props.piece?.top);
    const rightPattern = ETERNITY_PATTERNS.find(pattern => pattern.binaryInt === props.piece?.right);
    const bottomPattern = ETERNITY_PATTERNS.find(pattern => pattern.binaryInt === props.piece?.bottom);
    const leftPattern = ETERNITY_PATTERNS.find(pattern => pattern.binaryInt === props.piece?.left);

    // If any of the patterns are not found, raise an error
    if (!topPattern || !rightPattern || !bottomPattern || !leftPattern) {
        throw new Error("Pattern not found");
    }

    // Assign the correct orientation to the patterns
    topPattern.svg.direction = Direction.Top
    rightPattern.svg.direction = Direction.Right
    bottomPattern.svg.direction = Direction.Bottom
    leftPattern.svg.direction = Direction.Left

    return (
        <div style={{
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'center',
            alignItems: 'center',
            border: '1px solid black',
            width: "256px",
            height: "256px",
        }}>
            <svg xmlns="http://www.w3.org/2000/svg" version="1.1" width="256" height="256" viewBox="0 0 256 256">
                <g transform="translate(0, 0)">
                    <svg xmlns="http://www.w3.org/2000/svg" version="1.1" width="256" height="256" viewBox="-128 -128 256 256">
                        <polygon points="-128,-128 0,0 -128,128" fill={topPattern.svg.bg_color} stroke={topPattern.svg.bg_stroke} transform="rotate(90, 0, 0)"/>
                        <path d={topPattern.svg.path} fill={topPattern.svg.path_color} stroke={topPattern.svg.path_stroke} transform="rotate(90, 0, 0)"/>
                    </svg>
                </g>
                <g>
                    <svg xmlns="http://www.w3.org/2000/svg" version="1.1" width="256" height="256" viewBox="-128 -128 256 256">
                        <polygon points="-128,-128 0,0 -128,128" fill={rightPattern.svg.bg_color} stroke={rightPattern.svg.bg_stroke} transform="rotate(180, 0, 0)"/>
                        <path d={rightPattern.svg.path} fill={rightPattern.svg.path_color} stroke={rightPattern.svg.path_stroke} transform="rotate(180, 0, 0)"/>
                    </svg>
                </g>
                <g>
                    <svg xmlns="http://www.w3.org/2000/svg" version="1.1" width="256" height="256" viewBox="-128 -128 256 256">
                        <polygon points="-128,-128 0,0 -128,128" fill={bottomPattern.svg.bg_color} stroke={bottomPattern.svg.bg_stroke} transform="rotate(270, 0, 0)"/>
                        <path d={bottomPattern.svg.path} fill={bottomPattern.svg.path_color} stroke={bottomPattern.svg.path_stroke} transform="rotate(270, 0, 0)"/>
                    </svg>
                </g>
                <g>
                    <svg xmlns="http://www.w3.org/2000/svg" version="1.1" width="256" height="256" viewBox="-128 -128 256 256">
                        <polygon points="-128,-128 0,0 -128,128" fill={leftPattern.svg.bg_color} stroke={leftPattern.svg.bg_stroke}/>
                        <path d={leftPattern.svg.path} fill={leftPattern.svg.path_color} stroke={leftPattern.svg.path_stroke}/>
                    </svg>
                </g>
                <rect x="0" y="0" width="256" height="256" fill="none" stroke="black"/>
            </svg>
        </div>
    )
}

export default Piece;
