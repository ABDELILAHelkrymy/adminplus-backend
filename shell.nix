{ pkgs ? import <nixpkgs> {} }:

pkgs.mkShell {
  buildInputs = [
    (import ./python-packages.nix { inherit pkgs; })
    pkgs.gcc
    pkgs.libffi
    pkgs.zlib
    pkgs.libjpeg
    pkgs.libpng
    pkgs.libtiff
    pkgs.pkg-config
  ];
  
  shellHook = ''
    export PYTHONPATH=$PYTHONPATH:$(pwd)/src
  '';
}