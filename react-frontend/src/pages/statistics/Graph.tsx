import React from 'react';
import Plot from 'react-plotly.js';

const Graph = ({ data }) => {
    if (!data || !data.x || !data.y || !data.z) {
        return <div>Loading...</div>;
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
        title: 'Time over Size and Pattern Count',
        scene: {
            xaxis: { title: 'Size' },
            yaxis: { title: 'Pattern Count' },
            zaxis: { title: 'Time', type: 'log' }
        },
        autosize: true,
    };

    return (
        <Plot
            data={figData}
            layout={layout}
            style={{ width: "100%", height: "100%" }}
        />
    );
};

export default Graph;
