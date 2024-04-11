import Typography from "@mui/material/Typography";
import { Card, Container } from "@mui/material";
import CardContent from '@mui/material/CardContent';
import React from "react";
import Plot from 'react-plotly.js';

export const Stats = ({ data }) => {
    const isValidData = data && data.x && data.x.length > 0 && data.y && data.y.length > 0 && data.z && data.z.length > 0;

    if (!isValidData) {
        return (
            <div>
                <Typography variant="h4" gutterBottom>
                    Stats
                </Typography>
                <Card>
                    <CardContent>
                        <Typography>No data available.</Typography>
                    </CardContent>
                </Card>
            </div>
        );
    }

    const figData = [{
        type: 'surface',
        x: data.x,
        y: data.y,
        z: data.z,
        colorscale: 'Viridis',
        contours: {
            z: {
                show: true,
                usecolormap: true,
                highlightcolor: "limegreen",
                project: { z: true }
            }
        }
    }];

    const layout = {
        scene: {
            xaxis: { title: 'Size' },
            yaxis: { title: 'Pattern Count' },
            zaxis: { title: 'Time', type: 'log' }
        },
        autosize: true,
    };

    return (
        <div>
            <Container
                sx={{
                    display: 'flex',
                    justifyContent: 'center',
                    alignItems: 'center',
                    flexDirection: 'row',
                    flexWrap: 'wrap',
                    gap: 2,
                    padding: 2,
                }}
            >
                <Card>
                    <CardContent>
                        <Plot
                            data={figData}
                            layout={layout}
                            style={{ width: "100%", height: "100%" }}
                        />
                    </CardContent>
                </Card>
            </Container>
        </div>
    );
}
