import {SolverSolveResponse} from "../../proto/solver/v1/solver.ts";
import Typography from "@mui/material/Typography";
import {Card, Container} from "@mui/material";
import CardContent from '@mui/material/CardContent';

export const Stats = (props: { responses: SolverSolveResponse[] }) => {
    const lastResponse = props.responses[props.responses.length - 1];

    if (!lastResponse) {
        return <div>
            <Typography variant="h4">Stats</Typography>
            <Card>
                <CardContent>
                    <Typography>No Stats</Typography>
                </CardContent>
            </Card>
        </div>
    }
    return <div>
        <Typography variant="h4">Stats</Typography>
        <Container
            sx={{
                display: 'flex',
                justifyContent: 'center',
                alignItems: 'center',
                flexDirection: 'row',
                flexWrap: 'wrap',
                gap: 2,
                padding: 2,
            }
            }
        >
            <Card>
                <CardContent>
                    <Typography
                        sx={{fontSize: 14}}
                        color="text.secondary"
                        gutterBottom
                    >Time Elapsed</Typography>
                    <Typography variant="h5">{lastResponse.time}</Typography>
                </CardContent>
            </Card>

            <Card>
                <CardContent>
                    <Typography
                        sx={{fontSize: 14}}
                        color="text.secondary"
                        gutterBottom
                    >Hashes</Typography>
                    <Typography variant="h5">{lastResponse.hashTableSize}</Typography>
                </CardContent>
            </Card>

            <Card>
                <CardContent>
                    <Typography
                        sx={{fontSize: 14}}
                        color="text.secondary"
                        gutterBottom
                    >Hashes Per Second</Typography>
                    <Typography variant="h5">{lastResponse.hashesPerSecond.toFixed(3)}</Typography>
                </CardContent>
            </Card>

            <Card>
                <CardContent>
                    <Typography
                        sx={{fontSize: 14}}
                        color="text.secondary"
                        gutterBottom
                    >Boards Per Second</Typography>
                    <Typography variant="h5">{lastResponse.boardsPerSecond.toFixed(0)}</Typography>
                </CardContent>
            </Card>
            <Card>
                <CardContent>
                    <Typography
                        sx={{fontSize: 14}}
                        color="text.secondary"
                        gutterBottom
                    >Boards Checked</Typography>
                    <Typography variant="h5">{lastResponse.boardsAnalyzed}</Typography>
                </CardContent>
            </Card>

        </Container>


    </div>

}