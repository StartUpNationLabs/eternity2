{
  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-24.11";
    systems.url = "github:nix-systems/default";
    devenv.url = "github:cachix/devenv";
  };

  outputs = {
    nixpkgs,
    systems,
    ...
  }: let
    forEachSystem = nixpkgs.lib.genAttrs (import systems);
  in {
    packages =
      forEachSystem
      (system: let
        pkgs = nixpkgs.legacyPackages.${system};
        asio-grpc = pkgs.callPackage ./nix/asio-grpc.nix {};
        libunifex = pkgs.callPackage ./nix/libunifex.nix {};
        eternity2 = pkgs.stdenv.mkDerivation {
          pname = "eternity2";
          version = "1.0.0";
          src = ./.;
          nativeBuildInputs = [
            pkgs.cmake
            pkgs.ninja
            pkgs.pkg-config
          ];
          buildInputs = [
            pkgs.grpc
            asio-grpc
            libunifex
            pkgs.openssl
            pkgs.protobuf
            pkgs.hiredis
            pkgs.redis-plus-plus
            pkgs.catch2_3
          ];
        };
      in rec {
        inherit eternity2;
        default = eternity2;
        inherit asio-grpc;
        inherit libunifex;

        grpc-server-docker = pkgs.dockerTools.buildLayeredImage {
          name = "eternity2-grpc-server";
          config = {
            Cmd = ["${eternity2}/bin/asio-grpc-server"];
          };
        };
      });
  };
}
