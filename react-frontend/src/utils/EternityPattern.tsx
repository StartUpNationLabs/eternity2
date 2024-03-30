export interface SVG {
    name: string;
    bg_color: string;
    bg_stroke: string;
    path: string;
    path_color: string;
    path_stroke: string;
    direction: string;
}


export interface EternityPattern {
    name: string;
    binaryInt: number;
    bucasLetter: string;
    svg: SVG;
}


export interface EternityPatternProps {
    pattern: EternityPattern;
    onClick?: (pattern: EternityPattern) => void;
    onHover?: (pattern: EternityPattern) => void;
}
