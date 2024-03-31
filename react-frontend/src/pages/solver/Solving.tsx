import {Grid, Typography} from "@mui/material";
import Board from "../../components/Board.tsx";
import {useRecoilState, useRecoilValue} from "recoil";
import {boardState, settingsState} from "../requestForm/atoms.ts";
import {Stats} from "./Stats.tsx";
import {isSolvingState} from "./atoms.ts";
import {useEffect, useState} from "react";
import {solverClient} from "../../utils/Constants.tsx";
import {SolverSolveResponse} from "../../proto/solver/v1/solver.ts";
import {useStateHistory} from "../../utils/utils.tsx";


export const Solving = () => {

    const board = useRecoilValue(boardState);
    const setting = useRecoilValue(settingsState);
    const [solving, setSolving] = useRecoilState(isSolvingState);
    const [startedSolving, setStartedSolving] = useState(false);
    const [solverSolveResponse, setSolverSolveResponse] = useState<SolverSolveResponse>();
    useEffect(() => {
        if (solving && !startedSolving) {
            setStartedSolving(true);
            console.log("started solving");
            const stream = solverClient.solve({
                "hashThreshold": setting.hashThreshold,
                "pieces": board,
                "threads": setting.threads,
                "waitTime": setting.waitTime,
                solvePath: setting.path.path,
                useCache: setting.useCache,
                cachePullInterval: setting.cachePullInterval
            }, {});
            stream.responses.onMessage((message) => {
                setSolverSolveResponse(message);
            });

            stream.responses.onError((error) => {
                    setSolving(false);
                    setStartedSolving(false);
                }
            );

            stream.responses.onComplete(() => {
                setSolving(false);
                setStartedSolving(false);
            });
        }
    }, [solving, startedSolving, board, setting, solverSolveResponse, setSolverSolveResponse, setSolving]);


    return <Grid container spacing={2}
                 style={{minHeight: "100vh", height: '100%', display: 'flex', justifyContent: 'center', alignItems: 'center'}}>
        <Grid item xs={5}>
            <div
                style={{
                    padding: 20,
                    display: "flex",
                    flexDirection: "column",
                    alignItems: "center",
                    justifyContent: "center",
                    width: "100%",
                    margin: "auto",
                    marginTop: 20,
                }}
            >
                <Stats response={solverSolveResponse}/>
            </div>
        </Grid>
        <Grid item xs={4}>
            <div style={{
                display: 'flex',
                justifyContent: 'center',
                alignItems: 'center',
                height: '100%',
                aspectRatio: 1,
            }}>
                <div style={{width: "100%", height: "100%"}}>
                    <Board pieces={solverSolveResponse?.rotatedPieces || []}
                    />
                </div>
            </div>
        </Grid>
    </Grid>

}