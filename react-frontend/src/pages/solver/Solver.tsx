import {RequestForm} from "../requestForm/RequestForm.tsx";
import {Piece} from "../../proto/solver/v1/solver.ts";
import Board from "../../components/Board.tsx";
import {Grid} from "@mui/material";
import {useRecoilValue} from "recoil";
import {boardState} from "../requestForm/atoms.ts";
import {Solving} from "./Solving.tsx";


export const Solver = () => {
    const board = useRecoilValue(boardState);

    return <>
        <Grid container spacing={2}
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
                    <RequestForm/>
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
                        <Board pieces={board.map((piece: Piece) => {
                            return {
                                piece: piece,
                                index: 0,
                                rotation: 0,
                            }
                        })}/>
                    </div>
                </div>
            </Grid>
        </Grid>
        <Solving/>
    </>
}