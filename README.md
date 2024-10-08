# Eternity2 Project

This project consists of three main services: a gRPC server, an Envoy proxy, and a frontend application.

## Services

1. **gRPC Server**
   - Container name: grpc-server
   - Provides the core functionality of the application
   - Communicates using gRPC protocol

2. **Envoy Proxy**
   - Acts as a proxy between the frontend and the gRPC server
   - Translates HTTP/1.1 requests to gRPC
   - Exposes port 50052 for external communication

3. **Frontend**
   - Container name: frontend
   - Provides the user interface for the application
   - Runs on port 80

## Usage

1. Ensure Docker and Docker Compose are installed on your system.
2. Clone this repository.
3. Navigate to the project directory.
4. Run the following command to start all services:

   ```
   docker-compose up -d
   ```

5. Access the frontend application at `http://localhost:80`

## Environment Variables

Here's a table of all the environment variables that can be set:

| Service | Variable        | Description                                   | Default Value      |
|---------|-----------------|-----------------------------------------------|-------------------|
| Envoy   | SOLVER_API      | The hostname of the gRPC server               | grpc-server       |
| Frontend| SERVER_BASE_URL | The URL of the Envoy proxy (client-side)      | http://localhost:50052 |

## Networks

All services are connected to the `eternity2` network, allowing inter-container communication.
