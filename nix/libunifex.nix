{
  lib,
  stdenv,
  fetchFromGitHub,
  cmake,
}:
stdenv.mkDerivation rec {
  pname = "libunifex";
  version = "0.4.0";

  src = fetchFromGitHub {
    owner = "facebookexperimental";
    repo = "libunifex";
    rev = "v${version}";
    hash = "sha256-mdtTBl1w+PmyRBRU9J6mjU3xr8PEPd6xGMcOG4s9874=";
  };

  # fix invalid directory for package config <https://github.com/NixOS/nixpkgs/issues/144170>
  patches = [./0001-fix-absolute-path-package-config.patch];

  nativeBuildInputs = [
    cmake
  ];

  meta = {
    description = "Unified Executors";
    homepage = "https://github.com/facebookexperimental/libunifex";
    license = lib.licenses.asl20;
    mainProgram = "libunifex";
    platforms = lib.platforms.all;
  };
}
