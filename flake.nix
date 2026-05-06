{
  description = "Peoples Gas web client";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    pyproject-nix = {
      url = "github:pyproject-nix/pyproject.nix";
      inputs.nixpkgs.follows = "nixpkgs";
    };
    uv2nix = {
      url = "github:pyproject-nix/uv2nix";
      inputs.nixpkgs.follows = "nixpkgs";
      inputs.pyproject-nix.follows = "pyproject-nix";
    };
    pyproject-build-systems = {
      url = "github:pyproject-nix/build-system-pkgs";
      inputs.nixpkgs.follows = "nixpkgs";
      inputs.pyproject-nix.follows = "pyproject-nix";
      inputs.uv2nix.follows = "uv2nix";
    };
    flake-parts.url = "github:hercules-ci/flake-parts";
    flake-parts.inputs.nixpkgs-lib.follows = "nixpkgs";
    treefmt-nix.url = "github:numtide/treefmt-nix";
  };

  outputs = inputs @ {flake-parts, ...}:
    flake-parts.lib.mkFlake {inherit inputs;} {
      imports = [
        ./treefmt.nix
      ];
      systems = [
        "aarch64-darwin"
        "x86_64-darwin"
        "x86_64-linux"
      ];

      perSystem = {
        pkgs,
        lib,
        ...
      }: let
        # Load uv workspace from uv.lock + pyproject.toml
        workspace = inputs.uv2nix.lib.workspace.loadWorkspace {
          workspaceRoot = inputs.self;
        };

        # Create overlay from uv.lock
        overlay = workspace.mkPyprojectOverlay {
          sourcePreference = "wheel";
        };

        python = pkgs.python312;

        # Base Python package set from pyproject.nix
        pythonBase = pkgs.callPackage inputs.pyproject-nix.build.packages {
          inherit python;
        };

        # Compose full Python package set with build systems and uv deps
        pythonSet = pythonBase.overrideScope (
          lib.composeManyExtensions [
            inputs.pyproject-build-systems.overlays.wheel
            overlay
          ]
        );

        # Build the main package (no check during build)
        clientPackage = pythonSet.peoples-gas-lib.overrideAttrs (_old: {
          doCheck = false;
          doInstallCheck = false;
        });

        # Test virtualenv using pythonSet (not editable)
        testEnv = pythonSet.mkVirtualEnv "peoples-gas-lib-test-env" workspace.deps.all;

        # App: run tests with credentials for recording
        recordTestsApp = pkgs.writeShellApplication {
          name = "record-tests";
          runtimeInputs = [testEnv];
          text = ''
            if [ ! -f ./tests/integration/test_web_client.py ]; then
              echo "Error: Run this command from the repo root directory"
              exit 1
            fi
            export PYTHONDONTWRITEBYTECODE=1
            python -m pytest tests/integration/ -v --record-mode=rewrite --tb=short
          '';
        };
      in {
        packages.default = clientPackage;
        packages.client = clientPackage;
        packages.recordTestsApp = recordTestsApp;

        apps.record-tests = {
          type = "app";
          program = "${recordTestsApp}/bin/record-tests";
        };

        devShells.default = pkgs.mkShellNoCC {
          packages = [
            testEnv
            pkgs.uv
            pkgs.ruff
          ];
        };

        checks.nox =
          (pkgs.runCommand "peoples-gas-lib-nox" {
              nativeBuildInputs = [testEnv pkgs.uv];
              src = inputs.self;
              UV_NO_CACHE = "1";
              HOME = "$TMPDIR";
            } ''
              cp -r $src src
              chmod -R u+w src
              cd src
              nox
              touch $out
            '')
          // {
            meta = {
              description = "Run nox tasks for peoples-gas-lib";
              mainProgram = "nox";
            };
          };
      };
    };
}
