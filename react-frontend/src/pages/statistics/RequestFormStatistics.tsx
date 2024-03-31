import {Autocomplete, Checkbox, FormGroup, Slider, TextField, Typography} from "@mui/material";
import Button from "@mui/material/Button";

import {useRecoilState, useRecoilValue} from "recoil";

import Container from "@mui/material/Container";
import {isSolvingState} from "../solver/atoms.ts";
import {abortController, BOARD_SIZE_DEFAULT, BOARD_SIZE_MAX, BOARD_SIZE_MIN} from "../../utils/Constants.tsx";
import {useState} from "react";
import {
    Board,
    boardsState,
    boardState,
    pathsState
} from "../requestForm/atoms.ts";
import {generateBoards, settingsStatisticsState} from "./atoms.ts";


export const RequestFormStatistics = () => {
    const [settings, setSettings] = useRecoilState(settingsStatisticsState);
    const paths = useRecoilValue(pathsState);
    const pathOptions = ["Spiral", "Scan Row"]
    const [, setBoard] = useRecoilState(boardState);
    const [, setSolving] = useRecoilState(isSolvingState);
    const boards = useRecoilValue(boardsState);
    const setSelectedBoard = useState<Board | null>(null)[1];

    const [generatedBoards, setGeneratedBoards] = useState([] as Board[]);


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
                    Board size (min)
                </Typography>
                <Slider
                    defaultValue={BOARD_SIZE_DEFAULT}
                    min={BOARD_SIZE_MIN}
                    max={BOARD_SIZE_MAX}
                    value={settings.boardSizeMin}
                    onChange={
                        (_, v) => {
                            setSettings({
                                ...settings, boardSizeMin: v as number,
                            });
                        }
                    }
                    marks
                    step={1}
                    aria-labelledby={"input-slider-size"}
                    valueLabelDisplay="on"
                    size="small"
                />

                <Typography id="input-slider-size" gutterBottom>
                    Board size (max)
                </Typography>
                <Slider
                    defaultValue={BOARD_SIZE_DEFAULT}
                    min={BOARD_SIZE_MIN}
                    max={BOARD_SIZE_MAX}
                    value={settings.boardSizeMax}
                    onChange={
                        (_, v) => {
                            setSettings({
                                ...settings, boardSizeMax: v as number,
                            });
                        }
                    }
                    marks
                    step={1}
                    aria-labelledby={"input-slider-size"}
                    valueLabelDisplay="on"
                    size="small"
                />

                <Typography id="input-slider-pieces" gutterBottom>
                    Pattern count (min)
                </Typography>
                <Slider
                    defaultValue={1}
                    min={1}
                    max={22}
                    value={settings.patternSizeMin}
                    onChange={
                        (_, v) => {
                            setSettings({
                                ...settings, patternSizeMin: v as number,
                            });
                        }
                    }
                    marks
                    step={1}
                    aria-labelledby={"input-slider-pieces"}
                    valueLabelDisplay="on"
                    size="small"
                />
                <Typography id="input-slider-pieces" gutterBottom>
                    Pattern count (max)
                </Typography>
                <Slider
                    defaultValue={1}
                    min={1}
                    max={22}
                    value={settings.patternSizeMax}
                    onChange={
                        (_, v) => {
                            setSettings({
                                ...settings, patternSizeMax: v as number,
                            });
                        }
                    }
                    marks
                    step={1}
                    aria-labelledby={"input-slider-pieces"}
                    valueLabelDisplay="on"
                    size="small"
                />
                <Typography id="input-slider-pieces" gutterBottom>
                    Sample count
                </Typography>
                <Slider
                    defaultValue={1}
                    min={1}
                    max={10}
                    value={settings.sampleSize}
                    onChange={
                        (_, v) => {
                            setSettings({
                                ...settings, sampleSize: v as number,
                            });
                        }
                    }
                    marks
                    step={1}
                    aria-labelledby={"input-slider-pieces"}
                    valueLabelDisplay="on"
                    size="small"
                />
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
                    />
                </Container>
                <Typography id="input-slider-wait-time" gutterBottom>
                    Timeout
                </Typography>
                <Slider
                    defaultValue={1000}
                    min={50}
                    max={10000}
                    value={
                        settings.timeout
                    }
                    onChange={
                        (_, v) => setSettings({...settings, timeout: v as number})
                    }
                    marks
                    step={1000}
                    aria-labelledby={"input-slider-wait-time"}
                    valueLabelDisplay="on"
                    size="small"
                />
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
                        }
                        }
                >Solve
                </Button>
                <Button type="submit" color="primary"
                        onClick={() => {
                            const generatedBoards = generateBoards(settings.boardSizeMin, settings.boardSizeMax, settings.patternSizeMin, settings.patternSizeMax, settings.sampleSize);
                            setGeneratedBoards(generatedBoards);
                        }
                        }
                >Generate Boards
                </Button>
            </FormGroup>
            <Typography>
                Generated Boards {generatedBoards.length}
            </Typography>
        </>
    )
}
