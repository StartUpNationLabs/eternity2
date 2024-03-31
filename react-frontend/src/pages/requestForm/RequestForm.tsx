import {Autocomplete, Checkbox, FormGroup, Slider, TextField, Typography} from "@mui/material";
import Button from "@mui/material/Button";

import {useRecoilState, useRecoilValue} from "recoil";
import {
    Board,
    Path,
    BOARD_COLOR_DEFAULT,
    BOARD_COLOR_MAX,
    BOARD_COLOR_MIN,
    BOARD_SIZE_DEFAULT,
    BOARD_SIZE_MAX,
    BOARD_SIZE_MIN,
    boardsState,
    boardState,
    spiralPath,
    pathsState,
    settingsState,
    solveModeState
} from "./atoms.ts";
import Container from "@mui/material/Container";
import {convertToPieces, createBoard} from "../../utils/logic.tsx";
import {isSolvingMultiServerState, isSolvingState, isSolvingStepByStepState} from "../solver/atoms.ts";
import {abortController} from "../../utils/Constants.tsx";
import {Piece} from "../../proto/solver/v1/solver.ts";
import {useEffect, useState} from "react";


export const RequestForm = () => {
    const [settings, setSettings] = useRecoilState(settingsState);
    const paths = useRecoilValue(pathsState);
    const pathOptions = paths.filter((path) => path.path.length == settings.boardSize * settings.boardSize || path == spiralPath);
    const [, setBoard] = useRecoilState(boardState);
    const [, setSolving] = useRecoilState(isSolvingState);
    const [, setSolvingStepByStep] = useRecoilState(isSolvingStepByStepState);
    const [, setSolveMode] = useRecoilState(solveModeState);
    const [, setsolvingMultiServer] = useRecoilState(isSolvingMultiServerState);
    const boards = useRecoilValue(boardsState);
    const setSelectedBoard = useState<Board | null>(null)[1];

    useEffect(() => {
        const newBoard = convertToPieces(createBoard(BOARD_SIZE_DEFAULT, BOARD_COLOR_DEFAULT));
        setBoard(newBoard);
    }, [setBoard]);

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
                    onChange={
                        (_, v) => {
                            setSettings({
                                ...settings, boardSize: v as number, path: spiralPath
                            });
                            setSelectedBoard(null);
                            const newBoard = convertToPieces(createBoard(v as number, settings.boardColors));
                            setBoard(newBoard);
                        }
                    }
                    marks
                    step={1}
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
                    value={
                        settings.boardColors
                    }
                    onChange={
                        (_, v) => {
                            setSettings({...settings, boardColors: v as number});
                            const newBoard = convertToPieces(createBoard(settings.boardSize, v as number));
                            setBoard(newBoard);
                        }
                    }
                    marks
                    step={1}
                    aria-labelledby={"input-slider-colors"}
                    valueLabelDisplay="on"
                    size="small"
                />
            </FormGroup>

            {
                // ======= SELECT EXISTING BOARD ======= //
            }

            <div style={{width: "70%"}}>
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
                        getOptionLabel={(option) => option.label}
                        onChange={(_, v) => {
                            if (v) {
                                const pieceList = v.pieces.map((rotatedPiece) => rotatedPiece.piece).filter(piece => piece !== undefined) as Piece[];
                                setBoard(pieceList);
                                setSelectedBoard(v);
                                setSettings({
                                    ...settings,
                                    boardSize: Math.sqrt(pieceList.length)
                                });
                            }
                        }}
                    />
                </FormGroup>
            </div>

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
                        renderInput={(params) => <TextField
                            {...params}
                            variant="standard"
                            label="Paths"
                            placeholder="Paths"
                        />}
                        options={pathOptions}
                        value={settings.path}
                        onChange={(_, v) => {
                            if (v) {
                                setSettings({...settings, path: v});
                            }
                        }
                        }
                        isOptionEqualToValue={(option: Path, value: Path) => {
                            return option.label === value.label && option.path.length === value.path.length;
                        }
                        }
                    >
                    </Autocomplete>
                    <Typography id="input-slider-hash-threshold" gutterBottom>
                        Hash Threshold
                    </Typography>
                    <Slider
                        defaultValue={4}
                        min={1}
                        max={16}
                        value={
                            settings.hashThreshold
                        }
                        onChange={
                            (_, v) => setSettings({...settings, hashThreshold: v as number})
                        }
                        marks
                        step={1}
                        aria-labelledby={"input-slider-hash-threshold"}
                        valueLabelDisplay="on"
                        size="small"
                    />
                    <Typography id="input-slider-wait-time" gutterBottom>
                        Wait Time
                    </Typography>
                    <Slider
                        defaultValue={1000}
                        min={50}
                        max={2000}
                        value={
                            settings.waitTime
                        }
                        onChange={
                            (_, v) => setSettings({...settings, waitTime: v as number})
                        }
                        marks
                        step={100}
                        aria-labelledby={"input-slider-wait-time"}
                        valueLabelDisplay="on"
                        size="small"
                    />
                    <Typography id="input-slider-cache-pull-interval" gutterBottom>
                        Cache Pull Interval
                    </Typography>
                    <Slider
                        defaultValue={10}
                        min={1}
                        max={20}
                        value={
                            settings.cachePullInterval
                        }
                        onChange={
                            (_, v) => setSettings({...settings, cachePullInterval: v as number})
                        }
                        marks
                        step={1}
                        aria-labelledby={"input-slider-cache-pull-interval"}
                        valueLabelDisplay="on"
                        size="small"
                    />
                    <Typography id="input-slider-threads" gutterBottom>
                        Threads
                    </Typography>
                    <Slider
                        defaultValue={32}
                        min={1}
                        max={64}
                        value={
                            settings.threads
                        }
                        onChange={
                            (_, v) => setSettings({...settings, threads: v as number})
                        }
                        marks
                        step={1}
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
                    <Typography id={"use-cache"}>
                        Use Cache
                    </Typography>
                    <Checkbox
                        color="primary"
                        aria-labelledby={"use-cache"}
                        style={{
                            padding: 20,
                        }}
                        checked={settings.useCache}
                        onChange={(_, v) => setSettings({...settings, useCache: v})}
                    /></Container>
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
                <Button type="submit" color="primary"
                        onClick={() => {
                            abortController.abortController.abort();
                            abortController.abortController = new AbortController();
                            setSolving(true);
                            setSolveMode("normal");
                        }
                        }
                >Solve</Button>
                <Button type="submit" color="primary"
                        onClick={() => {
                            abortController.abortController.abort();
                            abortController.abortController = new AbortController();
                            setSolvingStepByStep(true);
                            setSolveMode("stepByStep");
                        }
                        }
                >Step By Step</Button>
                <Button type="submit" color="primary"
                        onClick={() => {
                            abortController.abortController.abort();
                            abortController.abortController = new AbortController();
                            setsolvingMultiServer(true);
                            setSolveMode("multiServer");
                        }
                        }
                >
                    Multi Server
                </Button>
            </FormGroup>
        </>
    )
}
