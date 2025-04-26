import {Grid, Typography} from "@mui/material";
import Board from "../../components/Board.tsx";
import {useRecoilState, useRecoilValue} from "recoil";
import {boardState, hintsState, settingsState} from "../requestForm/atoms.ts";
import {isSolvingStepByStepState} from "./atoms.ts";
import {useEffect, useState} from "react";
import {SolverStepByStepResponse} from "../../proto/solver/v1/solver.ts";
import {SolverClient} from "../../proto/solver/v1/solver.client.ts";
import {abortController, SERVER_BASE_URL} from "../../utils/Constants.tsx";
import {GrpcWebFetchTransport} from "@protobuf-ts/grpcweb-transport";
import {StatsStepByStep} from "./StatsStepByStep.tsx";


export const SolvingStepByStep = () => {

    const board = useRecoilValue(boardState);
    const setting = useRecoilValue(settingsState);
    const [solvingStepByStep, setsolvingStepByStep] = useRecoilState(isSolvingStepByStepState);
    const [startedsolvingStepByStep, setStartedsolvingStepByStep] = useState(false);
    const [solverSolveResponse, setSolverSolveResponse] = useState<SolverStepByStepResponse>();
    const [hints,] = useRecoilState(hintsState);


    useEffect(() => {
        if (solvingStepByStep && !startedsolvingStepByStep) {
            setStartedsolvingStepByStep(true);
            console.log("started solvingStepByStep");
            const transport = new GrpcWebFetchTransport({
                baseUrl: SERVER_BASE_URL,
                format: "binary",
                abort: abortController.abortController.signal,

            });
            const solverClient = new SolverClient(
                transport
            );

            const requestObj = {
                hashThreshold: setting.hashThreshold,
                pieces: board,
                threads: setting.threads,
                waitTime: setting.waitTime,
                solvePath: setting.path.path,
                useCache: setting.useCache,
                cachePullInterval: setting.cachePullInterval,
                hints: hints,
            }

            console.log("Request object: ", requestObj);

            const stream = solverClient.solveStepByStep(requestObj, {});
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
        // return cleanup;
    }, [solvingStepByStep, startedsolvingStepByStep, board, setting, solverSolveResponse, setSolverSolveResponse, setsolvingStepByStep]);

    useEffect(() => {
        return () => {
            abortController.abortController.abort();
            abortController.abortController = new AbortController();
        }
    }, []);

    return <Grid container spacing={2}
                 style={{
                     minHeight: "90vh",
                     height: '100%',
                     display: 'flex',
                     justifyContent: 'center',
                     alignItems: 'center'
                 }}>

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
        <Grid item xs={3}
              style={{
                  height: '100%',
              }}
        >
            <div
                style={{
                    padding: 20,
                    display: "flex",
                    flexDirection: "column",
                    alignItems: "center",
                    justifyContent: "center",
                    width: "100%",
                    height: "100%",
                    margin: "auto",
                    marginTop: 20,
                }}
            >
                <StatsStepByStep response={solverSolveResponse}/>
            </div>
        </Grid>
        <Grid item xs={4}>
            <Typography variant={"h4"}>Max Board
            </Typography>
            <div style={{
                display: 'flex',
                justifyContent: 'center',
                alignItems: 'center',
                height: '100%',
                aspectRatio: 1,
            }}>
                <div style={{width: "100%", height: "100%"}}>
                    <Board pieces={solverSolveResponse?.maxBoard || []}
                    />
                </div>
            </div>
        </Grid>
    </Grid>

}
