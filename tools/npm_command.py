"""Launch the explicitly installed npm with no shell or .cmd argument parsing."""
import os
from pathlib import Path
import shutil


def npm_command():
    npm = shutil.which('npm')
    if not npm:
        raise RuntimeError('Installed npm is required')
    if os.name != 'nt':
        return [npm]
    node = shutil.which('node')
    cli = Path(npm).parent / 'node_modules/npm/bin/npm-cli.js'
    if not node or not cli.is_file():
        raise RuntimeError('Windows proof requires the standard Node/npm installation layout')
    return [node, str(cli)]
