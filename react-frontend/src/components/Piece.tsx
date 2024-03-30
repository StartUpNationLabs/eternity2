import {Direction, ETERNITY_PATTERNS, Rotation} from "../utils/Constants";
import {RotatedPiece} from "../proto/solver/v1/solver";
import {EternityPattern} from "../utils/EternityPattern";

// Function to get the svg for a specific pattern given as input, as well as a rotation
function getSVG(pattern: EternityPattern, rotation: Rotation) {
    const angle: number = (pattern.svg.direction + rotation) * 90;
    return (
        <g>
            <svg xmlns="http://www.w3.org/2000/svg" version="1.1" width="100%" height="100%"
                 viewBox="-128 -128 256 256">
                <polygon points="-128,-128 0,0 -128,128" fill={pattern.svg.bg_color}
                         stroke={pattern.svg.bg_stroke} transform={`rotate(${angle}, 0, 0)`}/>
                <path d={pattern.svg.path} fill={pattern.svg.path_color}
                      stroke={pattern.svg.path_stroke} transform={`rotate(${angle}, 0, 0)`}/>
            </svg>
        </g>
    )
}

const Piece = (props: RotatedPiece) => {
    // Get the corresponding eternity pattern from the constants
    let topPattern = ETERNITY_PATTERNS.find(pattern => pattern.binaryInt === props.piece?.top);
    let rightPattern = ETERNITY_PATTERNS.find(pattern => pattern.binaryInt === props.piece?.right);
    let bottomPattern = ETERNITY_PATTERNS.find(pattern => pattern.binaryInt === props.piece?.bottom);
    let leftPattern = ETERNITY_PATTERNS.find(pattern => pattern.binaryInt === props.piece?.left);

    // If any of the patterns are not found, raise an error
    if (!topPattern || !rightPattern || !bottomPattern || !leftPattern) {
        throw new Error("Pattern not found");
    }

    // Deep copy the patterns and set the direction of the svg
    topPattern = {
        ...topPattern,
        svg: {
            ...topPattern.svg,
            direction: Direction.Top
        }
    }

    rightPattern = {
        ...rightPattern,
        svg: {
            ...rightPattern.svg,
            direction: Direction.Right
        }
    }

    bottomPattern = {
        ...bottomPattern,
        svg: {
            ...bottomPattern.svg,
            direction: Direction.Bottom
        }
    }

    leftPattern = {
        ...leftPattern,
        svg: {
            ...leftPattern.svg,
            direction: Direction.Left
        }
    }

    const rotation: Rotation = props.rotation + 1;

    return (
        <div style={{
            display: 'flex',
            position: "relative",
            width: "100%",
            height: "100%",
            aspectRatio: 1,
        }}>
            <svg xmlns="http://www.w3.org/2000/svg" version="1.1" viewBox="0 0 256 256" style={{position: "absolute"}}>
                {getSVG(topPattern, rotation)}
                {getSVG(rightPattern, rotation)}
                {getSVG(bottomPattern, rotation)}
                {getSVG(leftPattern, rotation)}
            </svg>
        </div>
    )
}

export default Piece;
