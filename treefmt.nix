{inputs, ...}: {
  imports = [inputs.treefmt-nix.flakeModule];
  perSystem = _: {
    treefmt = {
      settings.on-unmatched = "fatal"; # Ensure 100% coverage
      settings.excludes = [
        "*.lock"
        "tests/fixtures/*" # test fixtures, not source
      ];

      # GitHub Actions
      programs.actionlint.enable = true; # github action linter

      # Nix
      programs.alejandra.enable = true;

      programs.statix.enable = true;
      settings.statix.priority = 1;

      programs.deadnix.enable = true;
      settings.deadnix.priority = 2;

      # Python
      programs.ruff.format = true;

      programs.ruff.check = true;
      settings.formatter.ruff-check.priority = 1;

      # Markdown
      programs.mdformat.enable = true;

      # TOML
      programs.taplo.enable = true;
    };
  };
}
