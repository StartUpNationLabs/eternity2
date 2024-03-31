import {Grid, Typography} from "@mui/material";
import Board from "../../components/Board.tsx";
import {useRecoilState, useRecoilValue} from "recoil";
import {boardState, settingsState} from "../requestForm/atoms.ts";
import {Stats} from "./Stats.tsx";
import {isSolvingState, isSolvingStepByStepState} from "./atoms.ts";
import {useEffect, useState} from "react";
import {solverClient} from "../../utils/Constants.tsx";
import {SolverSolveResponse, SolverStepByStepResponse} from "../../proto/solver/v1/solver.ts";
import {useStateHistory} from "../../utils/utils.tsx";


export const SolvingStepByStep = () => {

    const board = useRecoilValue(boardState);
    const setting = useRecoilValue(settingsState);
    const [solvingStepByStep, setsolvingStepByStep] = useRecoilState(isSolvingStepByStepState);
    const [startedsolvingStepByStep, setStartedsolvingStepByStep] = useState(false);
    const [solverSolveResponse, setSolverSolveResponse] = useState<SolverStepByStepResponse>();
    useEffect(() => {
        if (solvingStepByStep && !startedsolvingStepByStep) {
            setStartedsolvingStepByStep(true);
            console.log("started solvingStepByStep");
            const stream = solverClient.solveStepByStep({
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
                    console.error(error);
                    setsolvingStepByStep(false);
                    setStartedsolvingStepByStep(false);
                }
            );

            stream.responses.onComplete(() => {
                console.log("stream ended");
                setsolvingStepByStep(false);
                setStartedsolvingStepByStep(false);
            });
        }
    }, [solvingStepByStep, startedsolvingStepByStep, board, setting, solverSolveResponse, setSolverSolveResponse, setsolvingStepByStep]);


    return <Grid container spacing={2}
                 style={{minHeight: "100vh", height: '100%',  display: 'flex', justifyContent: 'center', alignItems: 'center'}}>

        <Grid item xs={4}>
            <Typography variant={"h4"}>Current Board
            </Typography>
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
        {/*<Grid item xs={4}>*/}
        {/*    <Typography variant={"h4"}>Max Board*/}
        {/*    </Typography>*/}
        {/*    <div style={{*/}
        {/*        display: 'flex',*/}
        {/*        justifyContent: 'center',*/}
        {/*        alignItems: 'center',*/}
        {/*        height: '100%',*/}
        {/*        aspectRatio: 1,*/}
        {/*    }}>*/}
        {/*        <div style={{width: "100%", height: "100%"}}>*/}
        {/*            <Board pieces={getMaxBoard(solverSolveResponses) || []}*/}
        {/*            />*/}
        {/*        </div>*/}
        {/*    </div>*/}
        {/*</Grid>*/}
    </Grid>

}