from pathlib import Path
import subprocess
import sys

plugins_dir = Path(sys.argv[1])

for plugin_dir in plugins_dir.iterdir():
    if plugin_dir.is_dir():
        plugin_web_client = plugin_dir / f'girder_{plugin_dir.name}' / 'web_client'

        if plugin_web_client.exists() and (plugin_web_client / 'package-lock.json').exists():
            subprocess.run(
                'npm ci && npm run build',
                check=True,
                shell=True,
                stdout=sys.stdout,
                stderr=sys.stderr,
                cwd=plugin_web_client
            )
