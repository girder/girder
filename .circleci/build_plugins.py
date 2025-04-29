from pathlib import Path
import subprocess
import sys

plugins_dir = Path(sys.argv[1])

for plugin_dir in plugins_dir.iterdir():
    if plugin_dir.is_dir():
        search_dirs = [
            plugin_dir / f'girder_{plugin_dir.name}' / 'web_client',
            plugin_dir / f'girder_plugin_{plugin_dir.name}' / 'web_client',
            plugin_dir / plugin_dir.name / 'web_client',
        ]

        for web_client_dir in search_dirs:
            if web_client_dir.exists() and (web_client_dir / 'package-lock.json').exists():
                subprocess.run(
                    'npm ci && SKIP_SOURCE_MAPS=true npm run build',
                    check=True,
                    shell=True,
                    stdout=sys.stdout,
                    stderr=sys.stderr,
                    cwd=web_client_dir
                )
