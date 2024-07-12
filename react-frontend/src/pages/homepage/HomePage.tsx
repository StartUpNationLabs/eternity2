import {Card, CardContent, Typography} from "@mui/material";
import Button from "@mui/material/Button";
import {GrpcWebFetchTransport} from "@protobuf-ts/grpcweb-transport";
import {abortController} from "../../utils/Constants.tsx";
import {FeedClient} from "../../proto2/flightradar.client.ts";

export const HomePage = () => {


    const transport = new GrpcWebFetchTransport({
        baseUrl: "https://data-feed.flightradar24.com",
        format: "binary",
        abort: abortController.abortController.signal,
    });

    const solverClient = new FeedClient(
        transport
    );


    const stream = solverClient.liveFeed({
        "bounds": {
            "north": 53.46,
            "south": 52.6,
            "west": 2.7800000000000002,
            "east": 8.709999999999999
        },
        "settings": {
            "sourcesList": [
                0,
                1,
                2,
                3,
                4,
                5,
                6,
                7,
                8,
                9
            ],
            "servicesList": [
                0,
                1,
                2,
                3,
                4,
                5,
                6,
                7,
                8,
                9,
                10,
                11
            ],
            "trafficType": 3,
            "onlyRestricted": false
        },
        "fieldMask": {
            "pathsList": []
        },
        "stats": true,
        "maxage": 14400,
        "selectedFlightIdsList": [
            907804822
        ],
        "filtersList": [],
        "fleetsList": [],
        "limit": 1500,
        "restrictionMode": 0,
        highlightMode: false,
    }, {
        meta: {
            "Fr24-Device-Id": "web-1i2gvr3eg-At-QfVK6TuxNDDKPsCJ8u",
            "Fr24-Platform": "web-24.190.1214",
            "Origin": "https://www.flightradar24.com",
            "Referer": "https://www.flightradar24.com/",
            "X-User-Agent": "grpc-web-javascript/0.1",
            "x-envoy-retry-grpc-on": "unavailable",
            "TE": "trailers",
            'Authorization': "Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpc3MiOiJmbGlnaHRyYWRhcjI0LmNvbSIsImV4cCI6MTcyMzM3MzM1MywiaWF0IjoxNzIwNzgxMzUzLCJlbWFpbCI6ImFwcGFkb29hcG9vcnZhQGdtYWlsLmNvbSIsInVzZXJJZCI6MTYxMDk5MzEsImtleVNlc3Npb24iOiJmNTJhOWEzNTUyMjJiOWEwNTdjNWZjMTIxMmNhNzIwNmQwYTQ3ZjkyMTU0ODhmMGFhZjdiNzYzYTBjM2JjNDVlIiwic2wiOiJTIiwiYWwiOiIwIiwicGsiOiIifQ.lShOlDpCZXUgS-kv1NXkyMnKhNv4tPxlUquIkCHRu6s"
        },
        binaryOptions: {

        },

    });
    stream.responses.onMessage((message: any) => {
        console.log(message);
    });
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
