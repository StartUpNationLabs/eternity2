import { FC } from "react";
import { Box, Grid } from "@mui/material";
import { RotatedPiece } from "../../proto/solver/v1/solver.ts";
import DraggablePiece from "./DraggablePiece.tsx";

interface PiecePaletteProps {
    pieces: RotatedPiece[];
}

const PiecePalette: FC<PiecePaletteProps> = ({ pieces }) => {
    if (pieces.length === 0) {
        return (
            <Box 
                sx={{ 
                    display: 'flex', 
                    justifyContent: 'center', 
                    alignItems: 'center', 
                    height: '100%', 
                    color: 'text.secondary' 
                }}
            >
                No pieces available. Generate a new puzzle or complete the current one.
            </Box>
        );
    }

    return (
        <Grid container spacing={1}>
            {pieces.map((piece) => (
                <Grid item key={piece.index} xs={4} sm={3} md={4} lg={3}>
                    <Box 
                        sx={{ 
                            aspectRatio: '1/1',
                            border: '1px solid',
                            borderColor: 'divider',
                            borderRadius: 1,
                            p: 1,
                        }}
                    >
                        <DraggablePiece
                            piece={piece}
                            isDraggable={true}
                        />
                    </Box>
                </Grid>
            ))}
        </Grid>
    );
};

export default PiecePalette; 