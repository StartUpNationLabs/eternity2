import {Grid} from "@mui/material";
import Board from "../../components/Board.tsx";
import {useRecoilState, useRecoilValue} from "recoil";
import {boardState, settingsState} from "../requestForm/atoms.ts";
import {Stats} from "./Stats.tsx";
import {isSolvingState} from "./atoms.ts";
import React, {useEffect, useState} from "react";
import {solverClient} from "../../utils/Constants.tsx";
import {SolverSolveResponse} from "../../proto/solver/v1/solver.ts";

function useStateHistory<T>(
    initialValue?: T | (() => T)
): [T | undefined, (state: T) => void, Array<T>] {
    const [allStates, setState] = React.useReducer(
        (oldState: T[], newState: T) => {
            return [...oldState, newState];
        },
        typeof initialValue === "function"
            ? [(initialValue as () => T)()]
            : initialValue !== undefined
                ? [initialValue as T]
                : []
    );

    const currentState = allStates[allStates.length - 1];
    const stateHistory = allStates.slice(0, allStates.length - 1);
    return [currentState, setState, stateHistory];
}

export const Solving = () => {

    const board = useRecoilValue(boardState);
    const setting = useRecoilValue(settingsState);
    const [solving, setSolving] = useRecoilState(isSolvingState);
    const [startedSolving, setStartedSolving] = useState(false);
    const [solverSolveResponse, setSolverSolveResponse, solverSolveResponses] = useStateHistory<SolverSolveResponse>();
    useEffect(() => {
        if (solving && !startedSolving) {
            setStartedSolving(true);
            console.log("started solving");
            const stream = solverClient.solve({
                "hashThreshold": 11,
                "pieces": board,
                "threads": 16,
                "waitTime": 500,
                solvePath: setting.path.path,
                useCache: setting.useCache,
                cachePullInterval: 10,
            }, {});
            stream.responses.onMessage((message) => {
                console.log(message);
                setSolverSolveResponse(message);
            });

            stream.responses.onError((error) => {
                    console.error(error);
                    setSolving(false);
                    setStartedSolving(false);
                }
            );

            stream.responses.onComplete(() => {
                console.log("stream ended");
                setSolving(false);
                setStartedSolving(false);
            });
        }
    }, [solving, startedSolving, board, setting, solverSolveResponse, setSolverSolveResponse, setSolving]);


    return <Grid container spacing={2}
                 style={{height: '90vh', display: 'flex', justifyContent: 'center', alignItems: 'center'}}>

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
                <Stats responses={solverSolveResponses}/>
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