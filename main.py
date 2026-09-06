"""
Runs today's content generation across all active language plugins.
Each plugin runs fully (generate -> approve -> render -> approve ->
publish) before the next one starts, since Telegram approval is
blocking -- you'll be asked to approve/deny each language in turn.

To run only some plugins, edit ACTIVE_PLUGINS below.
"""
import sys
import importlib.util
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT_DIR / "core"))

from pipeline import run_plugin

PLUGINS_DIR = ROOT_DIR / "plugins"
ACTIVE_PLUGINS = ["german", "english", "french"]


def _load_plugin_config(plugin_dir: Path):
    """Loads a plugin's config.py as its own module (each plugin's file
    is literally named config.py, so this avoids them colliding)."""
    spec = importlib.util.spec_from_file_location(
        f"{plugin_dir.name}_config", plugin_dir / "config.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


if __name__ == "__main__":
    for plugin_name in ACTIVE_PLUGINS:
        plugin = _load_plugin_config(PLUGINS_DIR / plugin_name)
        run_plugin(plugin)
