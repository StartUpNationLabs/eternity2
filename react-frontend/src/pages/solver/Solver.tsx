import Container from "@mui/material/Container";
import {RequestForm} from "../requestForm/RequestForm.tsx";
import {RotatedPiece} from "../../proto/solver/v1/solver.ts";
import Board from "../../components/Board.tsx";

const rotatedPiece: RotatedPiece = {
    piece: {
        top: 0,
        right: 1,
        bottom: 2,
        left: 3
    },
    rotation: 0,
    index: 0
}

const gridSize = 4;
const rotatedPieces: RotatedPiece[] = Array.from({length: gridSize**2}, () => (rotatedPiece));

export const Solver = () => {


    return <Container
        style={
        {
                display: "flex",
                flexDirection: "row",
                height: "90vh",
                width: "100vw"
            }
        }
    >

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
        <div style={{
            display: 'flex',
            justifyContent: 'center',
            alignItems: 'center',
            height: '100vh',
            width: '100vw'
        }}>
            <div style={{width: "100%" , height: "100%"}}>
                <Board pieces={rotatedPieces}/>
            </div>
        </div>
    </Container>
}