# LSP-semgrep

LSP helper package that automatically installs and updates [semgrep](https://github.com/semgrep/semgrep) for you.

## Installation

 * Install [`LSP`](https://packagecontrol.io/packages/LSP) and `LSP-semgrep` from Package Control.
 * Restart Sublime.

The server is installed into a package-managed virtual environment using [uv](https://docs.astral.sh/uv/), which is
downloaded automatically. To use a `semgrep` binary of your own instead, set the `server_path` setting to its path.

## Configuration

Open the configuration file using the Command Palette `Preferences: LSP-semgrep Settings` command or open it from the Sublime menu.
