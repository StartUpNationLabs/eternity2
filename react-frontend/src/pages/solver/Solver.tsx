import { RequestForm } from "../requestForm/RequestForm.tsx";
import { Piece } from "../../proto/solver/v1/solver.ts";
import Board from "../../components/Board.tsx";
import { Grid } from "@mui/material";
import { useRecoilState, useRecoilValue } from "recoil";
import {
  boardState,
  hintsState,
  solveModeState,
} from "../requestForm/atoms.ts";
import { Solving } from "./Solving.tsx";
import { SolvingStepByStep } from "./SolvingStepByStep.tsx";
import { SolveMode } from "../../utils/Constants.tsx";

export const Solver = () => {
  const board = useRecoilValue(boardState);
  const [solveMode] = useRecoilState(solveModeState);
  const hints = useRecoilValue(hintsState);
  return (
    <>
      <Grid
        container
        spacing={2}
        style={{
          minHeight: "90vh",
          height: "100%",
          display: "flex",
          justifyContent: "space-around",
          alignItems: "center",
        }}
      >
        <Grid item xs={5}>
          <div
            style={{
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              justifyContent: "center",
              width: "100%",
              margin: "auto",
            }}
          >
            <RequestForm />
          </div>
        </Grid>
        <Grid item xs={4}>
          <div
            style={{
              display: "flex",
              justifyContent: "center",
              alignItems: "center",
              height: "100%",
              aspectRatio: 1,
            }}
          >
            <div style={{ width: "100%", height: "100%" }}>
              <Board
                hints={hints}
                pieces={board.map((piece: Piece) => {
                  return {
                    piece: piece,
                    index: 0,
                    rotation: 0,
                  };
                })}
              />
            </div>
          </div>
        </Grid>
      </Grid>
      {solveMode === SolveMode.normal && <Solving />}
      {solveMode === SolveMode.stepByStep && <SolvingStepByStep />}
    </>
  );
};
