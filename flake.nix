{
  description = "Python environment for AI-VoiceUsage";

  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-26.05";

  outputs = { self, nixpkgs }:
    let
      systems = [ "x86_64-linux" "aarch64-linux" "x86_64-darwin" "aarch64-darwin" ];
    in {
      devShells = nixpkgs.lib.genAttrs systems (system:
        let
          pkgs = nixpkgs.legacyPackages.${system};
        in {
          default = pkgs.mkShell {
            packages = [ (pkgs.python313.withPackages (ps: [ ps.tkinter ps.pyinstaller ])) ];
          };
        });
    };
}
