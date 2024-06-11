{
  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs/";
    utils.url = "github:numtide/flake-utils/";
  };

  outputs = {
    self,
    nixpkgs,
    utils,
  }: let
    out = system: let
      pkgs = import nixpkgs {
        inherit system;
        config.allowUnfree = true;
      };
    in {
      devShell = pkgs.mkShell {
        buildInputs = with pkgs; [
          alejandra
          poetry
          python3Full
          kubernetes
          argo
        ];
        PYTHONBREAKPOINT = "ipdb.set_trace";
        shellHook = ''
          export LD_LIBRARY_PATH=${pkgs.zlib.out}/lib:${pkgs.libgcc.lib}/lib:$LD_LIBRARY_PATH
          set -o allexport
          source .env
          set +o allexport
        '';
      };
    };
  in
    utils.lib.eachDefaultSystem out;
}
