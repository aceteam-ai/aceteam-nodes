{
  description = "AceTeam Nodes - Python workflow node library for local execution";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = import nixpkgs { inherit system; };

        libPathVar = if pkgs.stdenv.isDarwin then "DYLD_LIBRARY_PATH" else "LD_LIBRARY_PATH";
        runtimeLibs = with pkgs; [ stdenv.cc.cc ];
        libPath = pkgs.lib.makeLibraryPath runtimeLibs;

        wrappedUv = pkgs.writeShellScriptBin "uv" ''
          export ${libPathVar}="${libPath}:''$${libPathVar}"
          exec ${pkgs.uv}/bin/uv "$@"
        '';

      in
      {
        devShells.default = pkgs.mkShell {
          packages = [
            pkgs.python312
            wrappedUv
            pkgs.ruff
            pkgs.pyright
            pkgs.git
            pkgs.gh
          ];

          shellHook = ''
            export ${libPathVar}="${libPath}:''$${libPathVar}"

            echo ""
            echo "aceteam-nodes dev environment"
            echo ""
            echo "  Python $(python3 --version | cut -d' ' -f2) | uv | ruff | pyright"
            echo ""

            if [ -f ".venv/bin/activate" ]; then
              source .venv/bin/activate
              echo "  .venv activated"
            else
              echo "  Run: uv sync --extra dev"
            fi

            echo ""
            echo "  uv run pytest           # tests"
            echo "  uv run ruff check       # lint"
            echo "  uv build                # build"
            echo "  ./scripts/release.sh --dry-run  # release preview"
            echo ""
          '';
        };
      });
}
