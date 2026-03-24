import argparse
import concurrent.futures
import subprocess
import sys
from pathlib import Path


def build_plugins(
    plugins_dir: Path, max_workers: int = 8, rebuild: bool = False,
    extra: list[str] | None = None
) -> None:
    build_dirs = []
    if extra:
        build_dirs += extra
    for plugin_dir in plugins_dir.iterdir():
        if plugin_dir.is_dir():
            search_dirs = [
                plugin_dir / f'girder_{plugin_dir.name}' / 'web_client',
                plugin_dir / f'girder_plugin_{plugin_dir.name}' / 'web_client',
                plugin_dir / plugin_dir.name / 'web_client',
            ]

            for web_client_dir in search_dirs:
                if web_client_dir.exists() and (web_client_dir / 'package.json').exists() and (
                        rebuild or (web_client_dir / 'package-lock.json').exists()):
                    build_dirs.append(web_client_dir)

    with concurrent.futures.ThreadPoolExecutor(
        max_workers=min(max_workers, len(build_dirs))
    ) as executor:
        futures = {
            executor.submit(
                subprocess.run,
                ('npm ci' if not rebuild else
                 'rm -rf package-lock.json node_modules && npm install')
                + ' && SKIP_SOURCE_MAPS=true npm run build',
                check=True,
                shell=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.STDOUT,
                cwd=dir
            ): dir for dir in build_dirs
        }
        for future in concurrent.futures.as_completed(futures):
            dir = futures[future]
            try:
                future.result()
                print(f'Build completed for {dir}')
            except subprocess.CalledProcessError as e:
                print(f'Build failed for {dir}: {e}', file=sys.stderr)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Build web clients for plugins.')
    parser.add_argument(
        'plugins_dir', type=Path, help='Directory containing plugin directories.'
    )
    parser.add_argument(
        '--workers', type=int, default=8, help='Number of worker threads (default: 8).'
    )
    parser.add_argument(
        '--rebuild', action='store_true', default=False,
        help='Rebuild package-lock.json files and reinstall.'
    )
    parser.add_argument(
        '--extra', action='append',
        help='Additional directories to build; for example, use "." and '
        '"girder/web".',
    )
    args = parser.parse_args()

    build_plugins(args.plugins_dir, args.workers, args.rebuild, args.extra)
