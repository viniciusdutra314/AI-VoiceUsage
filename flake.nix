{
  description = "AI-VoiceUsage application and development environment";

  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-26.05";

  outputs = { nixpkgs, ... }:
    let
      forAllSystems = f: nixpkgs.lib.genAttrs
        [ "x86_64-linux" "aarch64-linux" "x86_64-darwin" "aarch64-darwin" ]
        (system: f nixpkgs.legacyPackages.${system});
    in {
      packages = forAllSystems (pkgs: {
        default = pkgs.writeShellApplication {
          name = "ai-voice-usage";
          text = ''
            exec ${pkgs.python313.withPackages (ps: [ ps.tkinter ])}/bin/python ${./ai_voice_usage.py} "$@"
          '';
        };
      });

      devShells = forAllSystems (pkgs: {
        default = pkgs.mkShell {
          packages = [ (pkgs.python313.withPackages (ps: [ ps.tkinter ps.pyinstaller ])) ];
          # Help PyInstaller find Tk's scripts in the Nix store.
          TK_LIBRARY = "${pkgs.tk}/lib/tk${pkgs.lib.versions.majorMinor pkgs.tk.version}";
        };
      });
    };
}
