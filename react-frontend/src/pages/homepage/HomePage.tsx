import {Card, CardContent, Typography} from "@mui/material";
import Button from "@mui/material/Button";

export const HomePage = () => {

    return (

        <div>
            <Card>
                <CardContent>
                    <Typography variant="h5" gutterBottom>
                        Welcome to Eternity 2 Solver
                    </Typography>
                    <Typography variant="body1">
                        Eternity 2 is a puzzle game where you need to solve a grid of
                        tiles.
                    </Typography>
                    <Typography variant="body1" gutterBottom>
                        Are you ready to start solving?
                    </Typography>
                    <Button
                        variant="contained"
                        color="primary"
                    >
                        Start Solver
                    </Button>
                </CardContent>
            </Card>
        </div>
    )
}
