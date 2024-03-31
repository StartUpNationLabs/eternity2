import {Autocomplete, Checkbox, FormGroup, Slider, TextField, Typography} from "@mui/material";
import Button from "@mui/material/Button";

import {useRecoilState, useRecoilValue} from "recoil";
import {boardState, defaultPath, Path, pathsState, settingsState} from "./atoms.ts";
import Container from "@mui/material/Container";
import {convertToBoard, convertToPieces, createBoard, shuffleAndRotateBoard} from "../../damien/logic.tsx";
import {isSolvingState} from "../solver/atoms.ts";


export const RequestForm = () => {
    const [settings, setSettings] = useRecoilState(settingsState);
    const paths = useRecoilValue(pathsState);
    const pathOptions = paths.filter((path) => path.path.length == settings.boardSize * settings.boardSize || path == defaultPath);
    const [board, setBoard] = useRecoilState(boardState);
    const [isSolving, setSolving] = useRecoilState(isSolvingState);
    return (
        <>

            <FormGroup
                style={{
                    padding: 20,
                    width: "100%",
                }}

            >
                <h2>Board Generation</h2>
                <Typography id="input-slider-size" gutterBottom>
                    Board size
                </Typography>
                <Slider
                    defaultValue={8}
                    min={2}
                    max={16}
                    value={
                        settings.boardSize
                    }
                    onChange={
                        (_, v) => {
                            setSettings({
                                ...settings, boardSize: v as number, path: defaultPath
                            })

                        }
                    }
                    marks
                    step={1}
                    aria-labelledby={"input-slider-size"}
                    valueLabelDisplay="on"


                />
                <Typography id="input-slider-colors" gutterBottom>
                    Number of Colors
                </Typography>
                <Slider
                    defaultValue={12}
                    min={4}
                    max={22}
                    value={
                        settings.boardColors
                    }
                    onChange={
                        (_, v) => setSettings({...settings, boardColors: v as number})
                    }
                    marks
                    step={1}
                    aria-labelledby={"input-slider-colors"}
                    valueLabelDisplay="on"
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
                            const board = convertToPieces(createBoard(settings.boardSize, settings.boardColors));
                            setBoard(board);
                        }}
                >Generate</Button>

                <Button type="submit" color="primary"
                        onClick={() => {
                            const b = convertToPieces(shuffleAndRotateBoard(convertToBoard(board)));
                            setBoard(b);
                        }}
                >Shuffle</Button>
            </FormGroup>
            <FormGroup
                style={{
                    padding: 20,
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
                </FormGroup>

            </FormGroup>
            <FormGroup
                style={{
                    padding: 20,
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
                ><Typography
                    id={"use-cache"}
                >
                    Use Cache
                </Typography>

                    <Checkbox

                        color="primary"
                        aria-labelledby={"use-cache"}
                        style={{
                            padding: 20,
                        }}
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
                            setSolving(true);
                        }
                        }
                >Solve</Button>
                <Button type="submit" color="primary">Step By Step</Button>
            </FormGroup>
        </>
    )
}
