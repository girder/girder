#!/usr/bin/env python

import base64
import json
import os
import subprocess
from typing import Optional

import click
from girder_client import GirderClient


def upload_cli(gc: GirderClient, image_name: str, replace: bool, cli_name: str, folder_id: str):
    output = subprocess.check_output(['docker', 'run', image_name, cli_name, '--xml'])
    gc.post('slicer_cli_web/cli', data={
        'folder': folder_id,
        'image': image_name,
        'name': cli_name,
        'replace': str(replace),
        'spec': base64.b64encode(output),
    })


@click.command()
@click.argument('api_url')
@click.argument('folder_id')
@click.argument('image_name')
@click.option('--cli', help='Push a single CLI with the given name', default=None)
@click.option('--replace', is_flag=True, help='Replace existing item if it exists', default=False)
def upload_slicer_cli_task(
    api_url: str, folder_id: str, image_name: str, cli: Optional[str], replace: bool
):
    if 'GIRDER_API_KEY' not in os.environ:
        raise Exception('Please set GIRDER_API_KEY in your environment.')

    gc = GirderClient(apiUrl=api_url)
    gc.authenticate(apiKey=os.environ['GIRDER_API_KEY'])

    output = subprocess.check_output(['docker', 'run', image_name, '--list_cli'])
    cli_list_json: dict = json.loads(output)

    # The keys are the names of each CLI in the image
    if cli:  # upload one
        if cli not in cli_list_json:
            raise ValueError('Invalid CLI name, not found in image CLI list.')
        upload_cli(gc, image_name, replace, cli, folder_id)
    else:  # upload all
        for cli_name in cli_list_json:
            upload_cli(gc, image_name, replace, cli_name, folder_id)


if __name__ == '__main__':
    upload_slicer_cli_task()
