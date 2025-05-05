import { RequestForm } from "../requestForm/RequestForm.tsx";
import { Piece } from "../../proto/solver/v1/solver.ts";
import Board from "../../components/Board.tsx";
import { Box, Card, CardContent, Grid, Typography, useTheme, useMediaQuery } from "@mui/material";
import { useRecoilState, useRecoilValue } from "recoil";
import {
  boardState,
  hintsState,
  solveModeState,
  settingsState,
} from "../requestForm/atoms.ts";
import { Solving } from "./Solving.tsx";
import { SolvingStepByStep } from "./SolvingStepByStep.tsx";
import { SolveMode } from "../../utils/Constants.tsx";
import { useEffect } from "react";
import { createBoard, convertToPieces } from "../../utils/logic.tsx";

// Default values for initial board
const DEFAULT_SOLVER_SIZE = 4;
const DEFAULT_SOLVER_COLORS = 8;

export const Solver = () => {
  const [board, setBoard] = useRecoilState(boardState);
  const [solveMode] = useRecoilState(solveModeState);
  const hints = useRecoilValue(hintsState);
  const [settings, setSettings] = useRecoilState(settingsState);
  const theme = useTheme();
  const isLargeScreen = useMediaQuery(theme.breakpoints.up('lg'));

  // Initialize board when component mounts
  useEffect(() => {
    if (board.length === 0) {
      // Create board with our custom defaults
      const newBoard = convertToPieces(createBoard(DEFAULT_SOLVER_SIZE, DEFAULT_SOLVER_COLORS));
      setBoard(newBoard);
      
      // Update settings to match the default board
      setSettings({
        ...settings,
        boardSize: DEFAULT_SOLVER_SIZE,
        boardColors: DEFAULT_SOLVER_COLORS,
      });
    }
  }, []);

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
        <div id={'solving-section'}
        >{(solveMode === SolveMode.normal || solveMode === SolveMode.stepByStep) && (
            <Box sx={{pt: 1.5, px: 1.5}}>
                <Card
                    elevation={0}
                    sx={{
                        bgcolor: 'background.paper',
                        border: '1px solid',
                        borderColor: 'divider',
                    }}
                >
                    <CardContent sx={{p: 3, '&:last-child': {pb: 3}}}>
                        {solveMode === SolveMode.normal && <Solving/>}
                        {solveMode === SolveMode.stepByStep && <SolvingStepByStep/>}
                    </CardContent>
                </Card>
            </Box>
        )}</div>
    </Box>
  );
};
