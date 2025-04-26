{
  lib,
  stdenv,
  fetchFromGitHub,
  cmake,
}:
stdenv.mkDerivation rec {
  pname = "asio-grpc";
  version = "3.4.3";

  src = fetchFromGitHub {
    owner = "Tradias";
    repo = "asio-grpc";
    rev = "v${version}";
    hash = "sha256-8xKAzN1EE1DhBSI1u2PYqNbvUct2IygXyQlqRD+PsYs=";
  };

  nativeBuildInputs = [
    cmake
  ];

  meta = {
    description = "Asynchronous gRPC with Asio/unified executors";
    homepage = "https://github.com/Tradias/asio-grpc?tab=readme-ov-file";
    license = lib.licenses.asl20;
    mainProgram = "asio-grpc";
    platforms = lib.platforms.all;
  };
}
