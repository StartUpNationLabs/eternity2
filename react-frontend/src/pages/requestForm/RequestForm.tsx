import {
  Autocomplete,
  Checkbox,
  FormGroup,
  Slider,
  TextField,
  Typography,
} from "@mui/material";
import Button from "@mui/material/Button";

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
import Container from "@mui/material/Container";
import { convertToPieces, createBoard } from "../../utils/logic.tsx";
import { isSolvingState, isSolvingStepByStepState } from "../solver/atoms.ts";
import {
  abortController,
  BOARD_COLOR_DEFAULT,
  BOARD_COLOR_MAX,
  BOARD_COLOR_MIN,
  BOARD_COLOR_STEP,
  BOARD_SIZE_DEFAULT,
  BOARD_SIZE_MAX,
  BOARD_SIZE_MIN,
  BOARD_SIZE_STEP,
  CACHE_PULL_INTERVAL_DEFAULT,
  CACHE_PULL_INTERVAL_MAX,
  CACHE_PULL_INTERVAL_MIN,
  CACHE_PULL_INTERVAL_STEP,
  DEFAULT_SPIRAL_PATH,
  HASH_THRESHOLD_DEFAULT,
  HASH_THRESHOLD_MAX,
  HASH_THRESHOLD_MIN,
  HASH_THRESHOLD_STEP,
  SCAN_ROW_PATH_NAME,
  SolveMode,
  THREADS_DEFAULT,
  THREADS_MAX,
  THREADS_MIN,
  THREADS_STEP,
  WAIT_TIME_DEFAULT,
  WAIT_TIME_MAX,
  WAIT_TIME_MIN,
  WAIT_TIME_STEP,
} from "../../utils/Constants.tsx";
import { Piece, SolverSolveRequest } from "../../proto/solver/v1/solver.ts";
import React, { useState } from "react";
import { numberOfColorsThatFitInABoard } from "../../utils/utils.tsx";
import { Board, Path } from "../../utils/interface.tsx";

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

  const handleBoardChange = (_: React.SyntheticEvent, v: Board) => {
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
      });
      setHints(v.hints);
      setSettings({
        // Choose the scan row path for size of the board
        ...settings,
        path:
          paths.find(
            (path) =>
              path.label === SCAN_ROW_PATH_NAME &&
              path.path.length === pieceList.length
          ) || DEFAULT_SPIRAL_PATH,
      });
    } else {
      setSelectedBoard(null);
      setSettings({
        ...settings,
        boardSize: BOARD_SIZE_DEFAULT,
        boardColors: BOARD_COLOR_DEFAULT,
      });
      setBoard(
        convertToPieces(createBoard(BOARD_SIZE_DEFAULT, BOARD_COLOR_DEFAULT))
      );
      setHints([]);
      setSelectedHintsTemplate(null);
    }
  };
  const handleBoardHintsChange = (_: React.SyntheticEvent, v: HintTemplate) => {
    if (v) {
      console.log("selected hints template", v);
      if (v) {
        const hints: SolverSolveRequest["hints"] = [];
        for (const selectedHintsTemplateElement of v.pieceIndex) {
          // iterate over original board

          hints.push({
            index: selectedHintsTemplateElement,
            x: selectedHintsTemplateElement % settings.boardSize,
            y: Math.floor(selectedHintsTemplateElement / settings.boardSize),
            rotation: 0,
          });
        }
        console.log("hints", hints);
        setHints(hints);
      }
      setSelectedHintsTemplate(v);
    } else {
      setHints([]);
      setSelectedHintsTemplate(null);
    }
  };

  return (
    <>
      <FormGroup
        style={{
          padding: 10,
          width: "100%",
        }}
      >
        <h2>Board Generation</h2>

        {
          // ======= BOARD SIZE SLIDER ======= //
        }

        <Typography id="input-slider-size" gutterBottom>
          Board size
        </Typography>
        <Slider
          defaultValue={BOARD_SIZE_DEFAULT}
          min={BOARD_SIZE_MIN}
          max={BOARD_SIZE_MAX}
          value={settings.boardSize}
          onChange={(event, v) => {
            handleBoardSizeChange(event, v);
          }}
          marks
          step={BOARD_SIZE_STEP}
          aria-labelledby={"input-slider-size"}
          valueLabelDisplay="on"
          size="small"
        />

        {
          // ======= BOARD COLOR SLIDER ======= //
        }

        <Typography id="input-slider-colors" gutterBottom>
          Number of Colors
        </Typography>
        <Slider
          defaultValue={BOARD_COLOR_DEFAULT}
          min={BOARD_COLOR_MIN}
          max={BOARD_COLOR_MAX}
          value={settings.boardColors}
          onChange={(event: Event, v) => {
            handleBoardColorChange(event, v);
          }}
          marks
          step={BOARD_COLOR_STEP}
          aria-labelledby={"input-slider-colors"}
          valueLabelDisplay="on"
          size="small"
        />
      </FormGroup>

      {
        // ======= SELECT EXISTING BOARD ======= //
      }

      <div
        style={{
          width: "80%",
        }}
      >
        <FormGroup>
          <Autocomplete
            id="boards"
            disablePortal
            renderInput={(params) => (
              <TextField
                {...params}
                variant="standard"
                label="Available Boards"
                placeholder="Board Name"
              />
            )}
            options={boards}
            value={selectedBoard}
            getOptionLabel={(option) => option.label}
            onChange={(event: React.SyntheticEvent, v) => {
              if (v !== null) {
                handleBoardChange(event, v);
              }
            }}
          />
        </FormGroup>
      </div>

      {
        // ======= SELECT EXISTING HINTS ======= //
      }

      <div
        style={{
          width: "80%",
        }}
      >
        <FormGroup>
          <Autocomplete
            id="hints"
            disablePortal
            renderInput={(params) => (
              <TextField
                {...params}
                variant="standard"
                label="Available Hints"
                placeholder="Hint Name"
              />
            )}
            options={hintTemplatesOptions}
            value={selectedHintsTemplate}
            getOptionLabel={(option) => option.label}
            onChange={(event: React.SyntheticEvent, v) => {
              if (v !== null) {
                handleBoardHintsChange(event, v);
              }
            }}
          />
        </FormGroup>
      </div>

      {
        // Generate and shuffle buttons
      }
      <FormGroup
        style={{
          display: "flex",
          flexDirection: "row",
          marginTop: 20,
          marginBottom: 20,
          gap: 20,
        }}
      >
        <Button
          variant="contained"
          type="submit"
          color="primary"
          disabled={selectedBoard !== null}
          onClick={() => {
            const newBoard = convertToPieces(
              createBoard(settings.boardSize, settings.boardColors)
            );
            setBoard(newBoard);
            setSelectedBoard(null);
          }}
        >
          Generate
        </Button>
        <Button
          variant="contained"
          type="submit"
          color="primary"
          disabled={selectedBoard !== null}
          onClick={() => {
            // Store the current board state before shuffling
            if (originalBoard === null) {
              setOriginalBoard([...board]);
            }

            // Shuffle the board
            const newBoard = [...board];

            setBoard(
              suffleWHints(
                originalBoard ?? newBoard,
                hints?.map((hint) => hint.index)
              )
            );
            setSelectedBoard(null);
            // hints on change
            if (selectedHintsTemplate) {
              handleBoardHintsChange(
                {} as React.SyntheticEvent,
                selectedHintsTemplate
              );
            }
          }}
        >
          Shuffle
        </Button>
        <Button
          variant="contained"
          type="submit"
          color="primary"
          disabled={originalBoard === null}
          onClick={() => {
            // Set the board state to the stored original board
            if (originalBoard !== null) {
              setBoard(originalBoard);
              setOriginalBoard(null);
            }
          }}
        >
          Unshuffle
        </Button>
      </FormGroup>

      <FormGroup
        style={{
          padding: 10,
          width: "100%",
        }}
      >
        <h2>Solver</h2>
        <FormGroup>
          <Autocomplete
            id="paths"
            renderInput={(params) => (
              <TextField
                {...params}
                variant="standard"
                label="Paths"
                placeholder="Paths"
              />
            )}
            options={pathOptions}
            value={settings.path}
            onChange={(_, v) => {
              if (v) {
                setSettings({ ...settings, path: v });
                // TODO: from where the fuck do i get hints ?
                // setHints(v.hints);
              }
            }}
            isOptionEqualToValue={(option: Path, value: Path) => {
              return (
                option.label === value.label &&
                option.path.length === value.path.length
              );
            }}
            style={{
              padding: 10,
            }}
          ></Autocomplete>
          <Typography id="input-slider-hash-threshold" gutterBottom>
            Hash Threshold
          </Typography>
          <Slider
            defaultValue={HASH_THRESHOLD_DEFAULT}
            min={HASH_THRESHOLD_MIN}
            max={HASH_THRESHOLD_MAX}
            value={settings.hashThreshold}
            onChange={(_, v) =>
              setSettings({ ...settings, hashThreshold: v as number })
            }
            marks
            step={HASH_THRESHOLD_STEP}
            aria-labelledby={"input-slider-hash-threshold"}
            valueLabelDisplay="on"
            size="small"
          />
          <Typography id="input-slider-wait-time" gutterBottom>
            Wait Time
          </Typography>
          <Slider
            defaultValue={WAIT_TIME_DEFAULT}
            min={WAIT_TIME_MIN}
            max={WAIT_TIME_MAX}
            value={settings.waitTime}
            onChange={(_, v) =>
              setSettings({ ...settings, waitTime: v as number })
            }
            marks
            step={WAIT_TIME_STEP}
            aria-labelledby={"input-slider-wait-time"}
            valueLabelDisplay="on"
            size="small"
          />
          <Typography id="input-slider-cache-pull-interval" gutterBottom>
            Cache Pull Interval
          </Typography>
          <Slider
            defaultValue={CACHE_PULL_INTERVAL_DEFAULT}
            min={CACHE_PULL_INTERVAL_MIN}
            max={CACHE_PULL_INTERVAL_MAX}
            value={settings.cachePullInterval}
            onChange={(_, v) =>
              setSettings({ ...settings, cachePullInterval: v as number })
            }
            marks
            step={CACHE_PULL_INTERVAL_STEP}
            aria-labelledby={"input-slider-cache-pull-interval"}
            valueLabelDisplay="on"
            size="small"
          />
          <Typography id="input-slider-threads" gutterBottom>
            Threads
          </Typography>
          <Slider
            defaultValue={THREADS_DEFAULT}
            min={THREADS_MIN}
            max={THREADS_MAX}
            value={settings.threads}
            onChange={(_, v) =>
              setSettings({ ...settings, threads: v as number })
            }
            marks
            step={THREADS_STEP}
            aria-labelledby={"input-slider-threads"}
            valueLabelDisplay="on"
            size="small"
          />
        </FormGroup>
      </FormGroup>

      <FormGroup
        style={{
          padding: 10,
          width: "100%",
          display: "flex",
          alignItems: "start",
        }}
      >
        <h2>Options</h2>
        <Container
          style={{
            display: "flex",
            flexDirection: "row",
            alignItems: "center",
          }}
        >
          <Typography id={"use-cache"}>Use Cache</Typography>
          <Checkbox
            color="primary"
            aria-labelledby={"use-cache"}
            style={{
              padding: 20,
            }}
            checked={settings.useCache}
            onChange={(_, v) => setSettings({ ...settings, useCache: v })}
          />
        </Container>
      </FormGroup>
      <FormGroup
        style={{
          padding: 20,
          width: "100%",
          flexDirection: "row",
          display: "flex",
          justifyContent: "center",
          gap: 20,
        }}
      >
        <Button
          type="submit"
          color="primary"
          onClick={() => {
            abortController.abortController.abort();
            abortController.abortController = new AbortController();
            if (selectedHintsTemplate) {
              handleBoardHintsChange(
                {} as React.SyntheticEvent,
                selectedHintsTemplate
              );
              console.log("selected hints template", selectedHintsTemplate);
            }
            setSolving(true);
            setSolveMode(SolveMode.normal);
          }}
        >
          Solve
        </Button>
        <Button
          type="submit"
          color="primary"
          onClick={() => {
            abortController.abortController.abort();
            abortController.abortController = new AbortController();
            setSolving(true);
            setSolveMode(SolveMode.stepByStep);
            setSolvingStepByStep(true);
          }}
        >
          Step By Step
        </Button>
      </FormGroup>
    </>
  );
};
