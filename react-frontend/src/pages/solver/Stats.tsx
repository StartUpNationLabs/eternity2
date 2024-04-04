import {SolverSolveResponse} from "../../proto/solver/v1/solver.ts";
import Typography from "@mui/material/Typography";
import {Card, Container} from "@mui/material";
import CardContent from '@mui/material/CardContent';

export const Stats = (props: { response?: SolverSolveResponse }) => {

    if (!props.response) {
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
                    <Typography variant="h5">{props.response.time}</Typography>
                </CardContent>
            </Card>

            <Card>
                <CardContent>
                    <Typography
                        sx={{fontSize: 14}}
                        color="text.secondary"
                        gutterBottom
                    >Hashes</Typography>
                    <Typography variant="h5">{props.response.hashTableSize}</Typography>
                </CardContent>
            </Card>

            <Card>
                <CardContent>
                    <Typography
                        sx={{fontSize: 14}}
                        color="text.secondary"
                        gutterBottom
                    >Hashes Per Second</Typography>
                    <Typography variant="h5">{props.response.hashesPerSecond.toFixed(3)}</Typography>
                </CardContent>
            </Card>

            <Card>
                <CardContent>
                    <Typography
                        sx={{fontSize: 14}}
                        color="text.secondary"
                        gutterBottom
                    >Boards Per Second</Typography>
                    <Typography variant="h5">{props.response.boardsPerSecond.toFixed(0)}</Typography>
                </CardContent>
            </Card>
            <Card>
                <CardContent>
                    <Typography
                        sx={{fontSize: 14}}
                        color="text.secondary"
                        gutterBottom
                    >Boards Checked</Typography>
                    <Typography variant="h5">{props.response.boardsAnalyzed}</Typography>
                </CardContent>
            </Card>
            <Card>
                <CardContent>
                    <Typography
                        sx={{fontSize: 14}}
                        color="text.secondary"
                        gutterBottom
                    >Hash Table Hits</Typography>
                    <Typography variant="h5">{props.response.hashTableHits.toFixed(0)}</Typography>
                </CardContent>
            </Card>
        </Container>


    </div>

}