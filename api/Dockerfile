FROM apoorvapewpew/eternity2-dependencies:latest

# Copy
WORKDIR /app
COPY . .

# Build
RUN cmake -B build -S . -DCMAKE_TOOLCHAIN_FILE=$VCPKG_ROOT/scripts/buildsystems/vcpkg.cmake
RUN cmake --build build


FROM scratch
COPY --from=builder /app/build/api/asio-grpc-server /app/asio-grpc-server

# Run
CMD ["/app/asio-grpc-server"]

EXPOSE 50051