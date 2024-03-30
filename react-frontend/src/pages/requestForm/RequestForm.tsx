import {
    FormGroup,
    Checkbox,
    Select,
    MenuItem,
    InputLabel,
    Slider,
    Typography
} from "@mui/material";
import Button from "@mui/material/Button";

import {useRecoilState} from "recoil";
import {settingsState} from "./atoms.ts";



export const RequestForm = () => {
    const [settings, setSettings] = useRecoilState(settingsState);


    return (

                <div
                    style={{
                    maxWidth:600,
                    display: "flex",
                    minHeight: "100vh",
                    flexDirection: "column",
                    gap: "2rem"

                }}>
                    <FormGroup

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
                                (_,v) => setSettings({...settings, boardSize: v as number})
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
                                (_,v)  => setSettings({...settings, boardColors: v as number})
                            }
                            marks
                            step={1}
                            aria-labelledby={"input-slider-colors"}
                        />

                    </FormGroup>

                    <FormGroup>
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
                        <FormGroup>
                            <Checkbox
                                id="checkbox"
                                name="checkbox"
                                title="Use Cache"
                                value={
                                    settings.useCache
                                }
                                onChange={
                                    (e) => setSettings({...settings, useCache: e.target.checked})
                                }
                            />
                        </FormGroup>
                    </FormGroup>

                    <Button type="submit" color="primary">Solve</Button>
                    <Button type="submit" color="primary">Step By Step</Button>
                </div>
            )}
