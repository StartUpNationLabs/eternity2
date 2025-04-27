import { RequestForm } from "../requestForm/RequestForm.tsx";
import { Piece } from "../../proto/solver/v1/solver.ts";
import Board from "../../components/Board.tsx";
import { Box, Card, CardContent, Grid, Typography, useTheme, useMediaQuery } from "@mui/material";
import { useRecoilState, useRecoilValue } from "recoil";
import {
  boardState,
  hintsState,
  solveModeState,
} from "../requestForm/atoms.ts";
import { Solving } from "./Solving.tsx";
import { SolvingStepByStep } from "./SolvingStepByStep.tsx";
import { SolveMode } from "../../utils/Constants.tsx";

export const Solver = () => {
  const board = useRecoilValue(boardState);
  const [solveMode] = useRecoilState(solveModeState);
  const hints = useRecoilValue(hintsState);
  const theme = useTheme();
  const isLargeScreen = useMediaQuery(theme.breakpoints.up('lg'));

  return (
    <Box 
      sx={{ 
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden',
        p: 2,
      }}
    >
      <Grid 
        container 
        spacing={3} 
        sx={{ 
          flex: 1,
          minHeight: 0,
          width: '100%',
          m: 0, // Reset margin
        }}
      >
        {/* Board Display */}
        <Grid 
          item 
          xs={12} 
          lg={7} 
          sx={{
            height: isLargeScreen ? '100%' : 'auto',
            minHeight: 0,
            p: '12px !important', // Override Grid padding
          }}
        >
          <Card 
            elevation={0}
            sx={{ 
              height: '100%',
              display: 'flex',
              flexDirection: 'column',
              bgcolor: 'background.paper',
              border: '1px solid',
              borderColor: 'divider',
            }}
          >
            <CardContent 
              sx={{ 
                flex: 1,
                p: 3,
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'center',
                minHeight: 0,
                '&:last-child': { pb: 3 },
              }}
            >
              <Box 
                sx={{
                  width: '100%',
                  height: '100%',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                }}
              >
                <Box
                  sx={{
                    width: 'min(100%, calc(100vh - 250px))',
                    aspectRatio: '1/1',
                  }}
                >
                  <Board
                    hints={hints}
                    pieces={board.map((piece: Piece) => ({
                      piece: piece,
                      index: 0,
                      rotation: 0,
                    }))}
                  />
                </Box>
              </Box>
            </CardContent>
          </Card>
        </Grid>

        {/* Controls */}
        <Grid 
          item 
          xs={12} 
          lg={5} 
          sx={{ 
            height: isLargeScreen ? '100%' : 'auto',
            minHeight: 0,
            p: '12px !important', // Override Grid padding
          }}
        >
          <Card 
            elevation={0}
            sx={{ 
              height: '100%',
              display: 'flex',
              flexDirection: 'column',
              bgcolor: 'background.paper',
              border: '1px solid',
              borderColor: 'divider',
              overflow: 'hidden',
            }}
          >
            <CardContent 
              sx={{ 
                p: 3,
                flex: 1,
                overflow: 'auto',
                '&:last-child': { pb: 3 },
              }}
            >
              <Typography 
                variant="h5" 
                component="h1" 
                gutterBottom
                sx={{ 
                  mb: 3,
                  fontWeight: 600,
                  color: 'text.primary'
                }}
              >
                Board Generation
              </Typography>
              <RequestForm />
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Solving Section */}
      {(solveMode === SolveMode.normal || solveMode === SolveMode.stepByStep) && (
        <Box sx={{ pt: 1.5, px: 1.5 }}>
          <Card 
            elevation={0}
            sx={{ 
              bgcolor: 'background.paper',
              border: '1px solid',
              borderColor: 'divider',
            }}
          >
            <CardContent sx={{ p: 3, '&:last-child': { pb: 3 } }}>
              {solveMode === SolveMode.normal && <Solving />}
              {solveMode === SolveMode.stepByStep && <SolvingStepByStep />}
            </CardContent>
          </Card>
        </Box>
      )}
    </Box>
  );
};
