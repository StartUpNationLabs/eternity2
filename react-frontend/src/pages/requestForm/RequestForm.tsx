import {Checkbox, FormGroup, InputLabel, MenuItem, Paper, Select, Slider, Typography} from "@mui/material";
import Button from "@mui/material/Button";

import {useRecoilState} from "recoil";
import {settingsState} from "./atoms.ts";
import Container from "@mui/material/Container";


export const RequestForm = () => {
    const [settings, setSettings] = useRecoilState(settingsState);


    return (
        <Paper
            style={{
                padding: 20,
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                justifyContent: "center",
                width: "50%",
                margin: "auto",
                marginTop: 20,

            }
            }
        >

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
                        (_, v) => setSettings({...settings, boardSize: v as number})
                    }
                    marks
                    step={1}
                    aria-labelledby={"input-slider-size"}
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
                />


            </FormGroup>
            <Button type="submit" color="primary">Generate</Button>

            <FormGroup
                style={{
                    padding: 20,
                    width: "100%",
                }}
            >
                <h2>Solver</h2>
                <FormGroup>
                    <InputLabel id="paths-label">Paths</InputLabel>
                    <Select
                        labelId="demo-simple-select-label"
                        id="demo-simple-select"
                        label="Paths"

                    >
                        <MenuItem value={10}>Ten</MenuItem>
                        <MenuItem value={20}>Twenty</MenuItem>
                        <MenuItem value={30}>Thirty</MenuItem>
                    </Select>
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

            <Button type="submit" color="primary">Solve</Button>
            <Button type="submit" color="primary">Step By Step</Button>
        </Paper>
    )
}
