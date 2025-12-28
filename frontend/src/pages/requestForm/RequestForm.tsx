import {
  Accordion,
  AccordionDetails,
  AccordionSummary,
  Autocomplete,
  Box,
  Checkbox,
  FormControl,
  FormGroup,
  FormLabel,
  Slider,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import Button from "@mui/material/Button";
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import UploadFileIcon from '@mui/icons-material/UploadFile';
import DownloadIcon from '@mui/icons-material/Download';

import { useRecoilState, useRecoilValue } from "recoil";
import {
  boardsState,
  boardState,
  hintsState,
  HintTemplate,
  hintTemplatesState,
  pathsState,
  settingsState,
  solveModeState,
} from "./atoms.ts";
import { SolverVersion } from "../../proto/solver/v1/solver.ts";
import { convertToPieces, createBoard } from "../../utils/logic.tsx";
import { isSolvingState, isSolvingStepByStepState } from "../solver/atoms.ts";
import { parsePuzzleCSV, exportPuzzleToCSV } from "../../utils/utils.tsx";
import {
  BOARD_COLOR_DEFAULT,
  BOARD_COLOR_MAX,
  BOARD_COLOR_MIN,
  BOARD_COLOR_STEP,
  BOARD_SIZE_DEFAULT,
  BOARD_SIZE_MAX,
  BOARD_SIZE_MIN,
  BOARD_SIZE_STEP,
  CACHE_PULL_INTERVAL_MAX,
  CACHE_PULL_INTERVAL_MIN,
  CACHE_PULL_INTERVAL_STEP,
  DEFAULT_SPIRAL_PATH,
  HASH_THRESHOLD_MAX,
  HASH_THRESHOLD_MIN,
  HASH_THRESHOLD_STEP,
  SCAN_ROW_PATH_NAME,
  SolveMode,
  THREADS_MAX,
  THREADS_MIN,
  THREADS_STEP,
  WAIT_TIME_MAX,
  WAIT_TIME_MIN,
  WAIT_TIME_STEP,
  abortController,
} from "../../utils/Constants.tsx";
import { Piece } from "../../proto/solver/v1/solver.ts";
import React, { useState } from "react";
import { numberOfColorsThatFitInABoard } from "../../utils/utils.tsx";
import { Board } from "../../utils/interface.tsx";

const suffleWHints = (
  originalArray: Piece[],
  hintsIndex: number[] = []
): Piece[] => {
  // don't shuffle the indexes of the hints
  const array = [...originalArray];
  const hints = hintsIndex.map((hintIndex) => array[hintIndex]);

  // shuffle the array without the hints
  const shuffledArray = array.filter((_, index) => !hintsIndex.includes(index));
  shuffledArray.sort(() => Math.random() - 0.5);

  // insert the hints in the shuffled array
  hintsIndex.forEach((hintIndex, index) => {
    shuffledArray.splice(hintIndex, 0, hints[index]);
  });
  console.log("shuffled array", shuffledArray.length);

  return shuffledArray;
};

export const RequestForm = () => {
  const [settings, setSettings] = useRecoilState(settingsState);
  const paths = useRecoilValue(pathsState);
  const pathOptions = paths.filter(
    (path) =>
      path.path.length == settings.boardSize * settings.boardSize ||
      path == DEFAULT_SPIRAL_PATH
  );
  const [board, setBoard] = useRecoilState(boardState);
  const [, setSolving] = useRecoilState(isSolvingState);
  const [, setSolvingStepByStep] = useRecoilState(isSolvingStepByStepState);
  const [, setSolveMode] = useRecoilState(solveModeState);
  const hintTemplates = useRecoilValue(hintTemplatesState);
  const hintTemplatesOptions = hintTemplates.filter(
    (hint) => hint.boardSize == settings.boardSize * settings.boardSize
  );
  const [hints, setHints] = useRecoilState(hintsState);
  const boards = useRecoilValue(boardsState);

  // Used to store the already defined selected board
  const [selectedBoard, setSelectedBoard] = useState<Board | null>(null);
  // Used to store the original board when a board is shuffled, we can then reset it
  const [originalBoard, setOriginalBoard] = useState<Piece[] | null>(null);
  // Used to store the selected hints
  const [selectedHintsTemplate, setSelectedHintsTemplate] =
    useState<HintTemplate | null>(null);
  console.log(hints);
  // useEffect(() => {
  //     if (board === null) {
  //
  //         const newBoard = convertToPieces(createBoard(settings.boardSize, settings.boardColors));
  //         setBoard(newBoard);
  //     }
  // }, [board, settings.boardSize, settings.boardColors, setBoard]);

  const handleBoardSizeChange = (_: Event, v: number | number[]) => {
    if (settings.boardColors > numberOfColorsThatFitInABoard(v as number)) {
      setSettings({
        ...settings,
        boardColors: numberOfColorsThatFitInABoard(v as number),
      });
    }

    // Update board size and then create a new board
    const newBoard = convertToPieces(
      createBoard(v as number, settings.boardColors)
    );
    setBoard(newBoard);

    // Reset the selected board
    setSelectedBoard(null);

    // Filter the current path as the SCAN_ROW_PATH_NAME with the new board size
    // Take the value from pathsState
    const scanRowPaths = paths.filter(
      (path) => path.label === SCAN_ROW_PATH_NAME
    );

    const boardSize = v as number;
    const scanRowPath = scanRowPaths.find(
      (path) => path.path.length === boardSize ** 2
    );

    setSettings({
      ...settings,
      boardSize: v as number,
      path: scanRowPath || DEFAULT_SPIRAL_PATH,
    });

    setHints([]);
    setSelectedHintsTemplate(null);
    setOriginalBoard(null);
  };

  const handleBoardColorChange = (_: Event, v: number | number[]) => {
    // Update board colors and then create a new board
    setSettings({ ...settings, boardColors: v as number });
    const newBoard = convertToPieces(
      createBoard(settings.boardSize, v as number)
    );
    setBoard(newBoard);

    // Reset the selected board
    setSelectedBoard(null);
    setHints([]);
    setSelectedHintsTemplate(null);
    setOriginalBoard(null);
  };

  const handleBoardChange = (_: React.SyntheticEvent, v: Board | null) => {
    if (v) {
      const pieceList = v.pieces
        .map((rotatedPiece) => rotatedPiece.piece)
        .filter((piece) => piece !== undefined) as Piece[];
      setBoard(pieceList);
      setSelectedBoard(v);
      setSettings({
        ...settings,
        boardSize: Math.sqrt(pieceList.length),
        boardColors: v.nbColors,
        path:
          paths.find(
            (path) =>
              path.label === SCAN_ROW_PATH_NAME &&
              path.path.length === pieceList.length
          ) || DEFAULT_SPIRAL_PATH,
      });
      setHints(v.hints);
    } else {
      setSelectedBoard(null);
      const newBoard = convertToPieces(createBoard(BOARD_SIZE_DEFAULT, BOARD_COLOR_DEFAULT));
      setBoard(newBoard);
      setSettings({
        ...settings,
        boardSize: BOARD_SIZE_DEFAULT,
        boardColors: BOARD_COLOR_DEFAULT,
      });
      setHints([]);
      setSelectedHintsTemplate(null);
    }
  };
  const handleBoardHintsChange = (
    _: React.SyntheticEvent,
    v: HintTemplate | null
  ) => {
    if (v) {
      setSelectedHintsTemplate(v);
      // Create hints from pieceIndex
      const newHints = v.pieceIndex.map(index => ({
        index,
        x: index % settings.boardSize,
        y: Math.floor(index / settings.boardSize),
        rotation: 0,
      }));
      setHints(newHints);
    } else {
      setSelectedHintsTemplate(null);
      setHints([]);
    }
  };

  const handleImportPuzzle = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    try {
      const fileContent = await file.text();
      const { pieces, boardSize, hints: importedHints } = parsePuzzleCSV(fileContent);

      // Update board with imported pieces
      setBoard(pieces);
      setSelectedBoard(null);
      setOriginalBoard(null);

      // Update settings to match imported puzzle
      const scanRowPaths = paths.filter(
        (path) => path.label === SCAN_ROW_PATH_NAME
      );
      const scanRowPath = scanRowPaths.find(
        (path) => path.path.length === boardSize ** 2
      );

      // Calculate number of colors from pieces
      const allColors = new Set<number>();
      pieces.forEach(piece => {
        if (piece.top !== 65535) allColors.add(piece.top);
        if (piece.right !== 65535) allColors.add(piece.right);
        if (piece.bottom !== 65535) allColors.add(piece.bottom);
        if (piece.left !== 65535) allColors.add(piece.left);
      });
      const nbColors = allColors.size;

      setSettings({
        ...settings,
        boardSize,
        boardColors: nbColors,
        path: scanRowPath || DEFAULT_SPIRAL_PATH,
      });

      // Set hints if any
      if (importedHints.length > 0) {
        setHints(importedHints);
      } else {
        setHints([]);
      }

      setSelectedHintsTemplate(null);
    } catch (error) {
      console.error('Error importing puzzle:', error);
      alert(`Failed to import puzzle: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }

    // Reset file input
    event.target.value = '';
  };

  const handleExportPuzzle = () => {
    if (board.length === 0) {
      alert('No puzzle to export. Please generate or import a puzzle first.');
      return;
    }

    try {
      const csvContent = exportPuzzleToCSV(board, settings.boardSize, hints);
      
      // Create a blob and download it
      const blob = new Blob([csvContent], { type: 'text/csv' });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `puzzle_size_${settings.boardSize}_colors_${settings.boardColors}.csv`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
    } catch (error) {
      console.error('Error exporting puzzle:', error);
      alert(`Failed to export puzzle: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  };

  return (
    <Stack spacing={4}>
      {/* Essential Controls */}
      <Box>
        <FormControl fullWidth>
          <Stack spacing={3}>
            <Box>
              <Typography 
                variant="subtitle2" 
                gutterBottom
                sx={{ color: 'text.secondary', mb: 1 }}
              >
                Board Size
              </Typography>
              <Slider
                value={settings.boardSize}
                onChange={handleBoardSizeChange}
                min={BOARD_SIZE_MIN}
                max={BOARD_SIZE_MAX}
                step={BOARD_SIZE_STEP}
                marks
                valueLabelDisplay="on"
                sx={{ 
                  '& .MuiSlider-markLabel': {
                    color: 'text.secondary',
                  }
                }}
              />
            </Box>

            <Box>
              <Typography 
                variant="subtitle2" 
                gutterBottom
                sx={{ color: 'text.secondary', mb: 1 }}
              >
                Number of Colors
              </Typography>
              <Slider
                value={settings.boardColors}
                onChange={handleBoardColorChange}
                min={BOARD_COLOR_MIN}
                max={BOARD_COLOR_MAX}
                step={BOARD_COLOR_STEP}
                marks
                valueLabelDisplay="on"
                sx={{ 
                  '& .MuiSlider-markLabel': {
                    color: 'text.secondary',
                  }
                }}
              />
            </Box>

            {/* Action Buttons - Moved up */}
            <Stack direction="row" spacing={2}>
        <Button
          variant="contained"
          onClick={() => {
            const newBoard = convertToPieces(
              createBoard(settings.boardSize, settings.boardColors)
            );
            setBoard(newBoard);
            setSelectedBoard(null);
          }}
                sx={{
                  flex: 1,
                  bgcolor: 'primary.main',
                  color: 'white',
                  '&:hover': {
                    bgcolor: 'primary.dark',
                  },
                }}
        >
          Generate
        </Button>
        <Button
                variant="outlined"
          onClick={() => {
            if (originalBoard === null) {
              setOriginalBoard([...board]);
            }
            const newBoard = [...board];
            setBoard(
              suffleWHints(
                originalBoard ?? newBoard,
                hints?.map((hint) => hint.index)
              )
            );
            setSelectedBoard(null);
            if (selectedHintsTemplate) {
              handleBoardHintsChange(
                {} as React.SyntheticEvent,
                selectedHintsTemplate
              );
            }
          }}
                sx={{
                  flex: 1,
                  borderColor: 'primary.main',
                  color: 'primary.main',
                  '&:hover': {
                    borderColor: 'primary.dark',
                    bgcolor: 'action.hover',
                  },
                }}
        >
          Shuffle
        </Button>
        <Button
                variant="outlined"
          onClick={() => {
            if (originalBoard !== null) {
              setBoard(originalBoard);
              setOriginalBoard(null);
            }
          }}
                disabled={!originalBoard}
                sx={{
                  flex: 1,
                  borderColor: 'primary.main',
                  color: 'primary.main',
                  '&:hover': {
                    borderColor: 'primary.dark',
                    bgcolor: 'action.hover',
                  },
                  '&.Mui-disabled': {
                    borderColor: 'action.disabled',
                    color: 'action.disabled',
                  },
                }}
        >
          Unshuffle
        </Button>
            </Stack>

            {/* Import/Export Puzzle Buttons */}
            <Stack direction="row" spacing={2}>
              <Box sx={{ flex: 1 }}>
                <input
                  accept=".csv"
                  style={{ display: 'none' }}
                  id="import-puzzle-input"
                  type="file"
                  onChange={handleImportPuzzle}
                />
                <label htmlFor="import-puzzle-input">
                  <Button
                    variant="outlined"
                    component="span"
                    fullWidth
                    startIcon={<UploadFileIcon />}
                    sx={{
                      borderColor: 'primary.main',
                      color: 'primary.main',
                      '&:hover': {
                        borderColor: 'primary.dark',
                        bgcolor: 'action.hover',
                      },
                    }}
                  >
                    Import Puzzle
                  </Button>
                </label>
              </Box>
              <Box sx={{ flex: 1 }}>
                <Button
                  variant="outlined"
                  fullWidth
                  startIcon={<DownloadIcon />}
                  onClick={handleExportPuzzle}
                  disabled={board.length === 0}
                  sx={{
                    borderColor: 'primary.main',
                    color: 'primary.main',
                    '&:hover': {
                      borderColor: 'primary.dark',
                      bgcolor: 'action.hover',
                    },
                    '&.Mui-disabled': {
                      borderColor: 'action.disabled',
                      color: 'action.disabled',
                    },
                  }}
                >
                  Export Puzzle
                </Button>
              </Box>
            </Stack>

            {/* Solve Buttons - Moved up */}
            <Stack direction="row" spacing={2}>
              <Button
                variant="contained"
                onClick={() => {
                  abortController.abortController.abort();
                  abortController.abortController = new AbortController();
                  if (selectedHintsTemplate) {
                    handleBoardHintsChange(
                      {} as React.SyntheticEvent,
                      selectedHintsTemplate
                    );
                  }
                  setSolving(true);
                  setSolveMode(SolveMode.normal);
                }}
                sx={{
                  flex: 1,
                  bgcolor: 'secondary.main',
                  color: 'white',
                  '&:hover': {
                    bgcolor: 'secondary.dark',
                  },
                }}
              >
                Solve
              </Button>
              <Button
                variant="contained"
                onClick={() => {
                  abortController.abortController.abort();
                  abortController.abortController = new AbortController();
                  setSolving(true);
                  setSolveMode(SolveMode.stepByStep);
                  setSolvingStepByStep(true);
                }}
                sx={{
                  flex: 1,
                  bgcolor: 'secondary.main',
                  color: 'white',
                  '&:hover': {
                    bgcolor: 'secondary.dark',
                  },
                }}
              >
                Step By Step
              </Button>
            </Stack>
          </Stack>
        </FormControl>
      </Box>

      {/* Advanced Settings Accordion */}
      <Accordion 
        elevation={0}
        sx={{ 
          bgcolor: 'transparent',
          '&:before': { display: 'none' },
        }}
      >
        <AccordionSummary
          expandIcon={<ExpandMoreIcon />}
          sx={{
            px: 0,
            '& .MuiAccordionSummary-content': {
              my: 0,
            },
          }}
        >
          <Typography 
            variant="subtitle1"
            sx={{ 
              fontWeight: 600,
              color: 'text.primary',
            }}
          >
            Advanced Settings
          </Typography>
        </AccordionSummary>
        <AccordionDetails sx={{ px: 0, pt: 0 }}>
          <Stack spacing={4}>
            {/* Board Configuration */}
            <Box>
              <FormControl fullWidth>
                <FormLabel 
                  sx={{ 
                    mb: 2,
                    color: 'text.primary',
                    '&.Mui-focused': {
                      color: 'text.primary',
                    }
                  }}
                >
                  Additional Board Options
                </FormLabel>
                <Stack spacing={3}>
                  <Box>
                    <Typography 
                      variant="subtitle2" 
                      gutterBottom
                      sx={{ color: 'text.secondary', mb: 1 }}
                    >
                      Available Boards
                    </Typography>
                    <Autocomplete
                      value={selectedBoard}
                      onChange={handleBoardChange}
                      options={boards}
                      getOptionLabel={(option) => option.label}
                      renderInput={(params) => (
                        <TextField
                          {...params}
                          placeholder="Select a board"
                          size="small"
                        />
                      )}
                      sx={{ 
                        '& .MuiOutlinedInput-root': {
                          bgcolor: 'background.paper',
                        }
                      }}
                    />
                  </Box>

                  <Box>
                    <Typography 
                      variant="subtitle2" 
                      gutterBottom
                      sx={{ color: 'text.secondary', mb: 1 }}
                    >
                      Available Hints
                    </Typography>
          <Autocomplete
                      value={selectedHintsTemplate}
                      onChange={handleBoardHintsChange}
                      options={hintTemplatesOptions}
                      getOptionLabel={(option) => option.label}
            renderInput={(params) => (
              <TextField
                {...params}
                          placeholder="Select hints"
                          size="small"
                        />
                      )}
                      sx={{ 
                        '& .MuiOutlinedInput-root': {
                          bgcolor: 'background.paper',
                        }
                      }}
                    />
                  </Box>
                </Stack>
              </FormControl>
            </Box>

            {/* Solver Settings */}
            <Box>
              <FormControl fullWidth>
                <FormLabel 
                  sx={{ 
                    mb: 2,
                    color: 'text.primary',
                    '&.Mui-focused': {
                      color: 'text.primary',
                    }
                  }}
                >
                  Solver Settings
                </FormLabel>
                <Stack spacing={3}>
                  <Box>
                    <Typography 
                      variant="subtitle2" 
                      gutterBottom
                      sx={{ color: 'text.secondary', mb: 1 }}
                    >
                      Solver Version
                    </Typography>
                    <Autocomplete
                      value={settings.solverVersion === SolverVersion.V1 ? SolverVersion.V1 : SolverVersion.V2}
                      onChange={(_, v) => {
                        if (v !== null) {
                          setSettings({ 
                            ...settings, 
                            solverVersion: v 
                          });
                        }
                      }}
                      options={[SolverVersion.V1, SolverVersion.V2]}
                      getOptionLabel={(option) => {
                        if (option === SolverVersion.V1) return "Solver V1 (Baseline)";
                        if (option === SolverVersion.V2) return "Solver V2 (Optimized)";
                        return "Unknown";
                      }}
                      renderInput={(params) => (
                        <TextField
                          {...params}
                          placeholder="Select solver version"
                          size="small"
                        />
                      )}
                      sx={{ 
                        '& .MuiOutlinedInput-root': {
                          bgcolor: 'background.paper',
                        }
                      }}
                    />
                  </Box>

                  <Box>
                    <Typography 
                      variant="subtitle2" 
                      gutterBottom
                      sx={{ color: 'text.secondary', mb: 1 }}
                    >
                      Path
                    </Typography>
                    <Autocomplete
            value={settings.path}
            onChange={(_, v) => {
              if (v) {
                setSettings({ ...settings, path: v });
                        }
                      }}
                      options={pathOptions}
                      getOptionLabel={(option) => option.label}
                      renderInput={(params) => (
                        <TextField
                          {...params}
                          placeholder="Select a path"
                          size="small"
                        />
                      )}
                      sx={{ 
                        '& .MuiOutlinedInput-root': {
                          bgcolor: 'background.paper',
                        }
                      }}
                    />
                  </Box>

                  <Box>
                    <Typography 
                      variant="subtitle2" 
                      gutterBottom
                      sx={{ color: 'text.secondary', mb: 1 }}
                    >
            Hash Threshold
          </Typography>
          <Slider
            value={settings.hashThreshold}
            onChange={(_, v) =>
              setSettings({ ...settings, hashThreshold: v as number })
            }
                      min={HASH_THRESHOLD_MIN}
                      max={HASH_THRESHOLD_MAX}
                      step={HASH_THRESHOLD_STEP}
            marks
                      valueLabelDisplay="auto"
                      sx={{ 
                        '& .MuiSlider-markLabel': {
                          color: 'text.secondary',
                        }
                      }}
                    />
                  </Box>

                  <Box>
                    <Typography 
                      variant="subtitle2" 
                      gutterBottom
                      sx={{ color: 'text.secondary', mb: 1 }}
                    >
                      Wait Time (ms)
          </Typography>
          <Slider
            value={settings.waitTime}
            onChange={(_, v) =>
              setSettings({ ...settings, waitTime: v as number })
            }
                      min={WAIT_TIME_MIN}
                      max={WAIT_TIME_MAX}
                      step={WAIT_TIME_STEP}
            marks
                      valueLabelDisplay="auto"
                      sx={{ 
                        '& .MuiSlider-markLabel': {
                          color: 'text.secondary',
                        }
                      }}
                    />
                  </Box>

                  <Box>
                    <Typography 
                      variant="subtitle2" 
                      gutterBottom
                      sx={{ color: 'text.secondary', mb: 1 }}
                    >
                      Cache Pull Interval (s)
          </Typography>
          <Slider
            value={settings.cachePullInterval}
            onChange={(_, v) =>
              setSettings({ ...settings, cachePullInterval: v as number })
            }
                      min={CACHE_PULL_INTERVAL_MIN}
                      max={CACHE_PULL_INTERVAL_MAX}
                      step={CACHE_PULL_INTERVAL_STEP}
            marks
                      valueLabelDisplay="auto"
                      sx={{ 
                        '& .MuiSlider-markLabel': {
                          color: 'text.secondary',
                        }
                      }}
                    />
                  </Box>

                  <Box>
                    <Typography 
                      variant="subtitle2" 
                      gutterBottom
                      sx={{ color: 'text.secondary', mb: 1 }}
                    >
            Threads
          </Typography>
          <Slider
            value={settings.threads}
            onChange={(_, v) =>
              setSettings({ ...settings, threads: v as number })
            }
                      min={THREADS_MIN}
                      max={THREADS_MAX}
                      step={THREADS_STEP}
            marks
                      valueLabelDisplay="auto"
                      sx={{ 
                        '& .MuiSlider-markLabel': {
                          color: 'text.secondary',
                        }
                      }}
                    />
                  </Box>

                  <FormGroup>
                    <Stack direction="row" spacing={2} alignItems="center">
          <Checkbox
            checked={settings.useCache}
            onChange={(_, v) => setSettings({ ...settings, useCache: v })}
                        sx={{ 
                          color: 'text.secondary',
                          '&.Mui-checked': {
                            color: 'primary.main',
                          }
                        }}
                      />
                      <Typography variant="body2" sx={{ color: 'text.secondary' }}>
                        Use Cache
                      </Typography>
                    </Stack>
      </FormGroup>
                </Stack>
              </FormControl>
            </Box>
          </Stack>
        </AccordionDetails>
      </Accordion>
    </Stack>
  );
};
