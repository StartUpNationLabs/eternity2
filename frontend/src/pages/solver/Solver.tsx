import React from "react";
import { RequestForm } from "../requestForm/RequestForm.tsx";
import { Piece } from "../../proto/solver/v1/solver.ts";
import Board from "../../components/Board.tsx";
import { Box, Card, CardContent, Grid, Typography, useTheme, useMediaQuery, Button } from "@mui/material";
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
import html2canvas from "html2canvas";

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

  // Add a ref to the board container
  const boardRef = React.useRef<HTMLDivElement>(null);
  // Add a ref for the cutting guide board
  const cuttingGuideRef = React.useRef<HTMLDivElement>(null);
  const [exportingCuttingGuide, setExportingCuttingGuide] = React.useState(false);

  // Function to handle export
  const handleExportPNG = async () => {
    if (boardRef.current) {
      const canvas = await html2canvas(boardRef.current, {
        backgroundColor: null,
        useCORS: true,
        logging: false,
        scale: 2,
      });
      const link = document.createElement("a");
      link.download = "eternity2-board.png";
      link.href = canvas.toDataURL("image/png");
      link.click();
    }
  };

  // Function to handle export with cutting guide
  const handleExportPNGWithGuide = async () => {
    setExportingCuttingGuide(true);
    // Wait for the next render
    setTimeout(async () => {
      if (cuttingGuideRef.current) {
        const canvas = await html2canvas(cuttingGuideRef.current, {
          backgroundColor: null,
          useCORS: true,
          logging: false,
          scale: 2,
        });
        const link = document.createElement("a");
        link.download = "eternity2-board-cutting-guide.png";
        link.href = canvas.toDataURL("image/png");
        link.click();
      }
      setExportingCuttingGuide(false);
    }, 50);
  };

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
                  ref={boardRef}
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
              {/* Export to PNG Button */}
              <Box sx={{ display: 'flex', justifyContent: 'center', my: 2, gap: 2 }}>
                <Button variant="contained" color="secondary" onClick={handleExportPNG}>
                  Export to PNG
                </Button>
                <Button variant="contained" color="secondary" onClick={handleExportPNGWithGuide}>
                  Export to PNG with cutting guide
                </Button>
              </Box>
              {/* Hidden board for cutting guide export */}
              {exportingCuttingGuide && (
                <Box ref={cuttingGuideRef} sx={{ position: 'absolute', left: -9999, top: 0, width: '400px', height: '400px' }}>
                  <Board
                    hints={hints}
                    pieces={board.map((piece: Piece) => ({
                      piece: piece,
                      index: 0,
                      rotation: 0,
                    }))}
                    showCuttingGuide={true}
                  />
                </Box>
              )}
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
