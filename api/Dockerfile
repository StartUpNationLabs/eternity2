# FROM apoorvapewpew/eternity2-dependencies:latest as builder
FROM ghcr.io/startupnationlabs/eternity2/base:latest as builder

# Copy
WORKDIR /app
COPY . .

RUN rm -rf vcpkg.json

# Build
RUN cmake -B build -S . -DCMAKE_TOOLCHAIN_FILE=$VCPKG_ROOT/scripts/buildsystems/vcpkg.cmake
RUN cmake --build build


FROM scratch as final
COPY --from=builder /app/build/api/asio-grpc-server /app/asio-grpc-server

# Run
CMD ["/app/asio-grpc-server"]

EXPOSE 50051

# Metadata
LABEL project="eternity2"
LABEL description="Eternity II Asio gRPC server"
LABEL version="1.0"
LABEL repository="https://github.com/StartUpNationLabs/eternity2"
