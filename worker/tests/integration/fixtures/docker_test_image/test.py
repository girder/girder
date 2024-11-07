import os
import sys
import time
import signal
import click
import json


@click.group()
def cli():
    pass


@cli.command()
@click.option('-m', type=str)
def stdio(m):
    print(m)


@cli.command()
@click.option('-m', type=str)
@click.option('-p', default='/mnt/girder_worker/data/output_pipe', type=click.File('w'))
def write(m, p):
    p.write(m)


@cli.command()
@click.option('-p', default='/mnt/girder_worker/data/input_pipe', type=click.File('r'))
def read(p):
    print(p.read())


@cli.command()
def sigkill():
    time.sleep(30)


@cli.command()
def sigterm():
    def _signal_handler(signal, frame):
        sys.exit(0)
    # Install signal handler
    signal.signal(signal.SIGTERM, _signal_handler)
    time.sleep(30)


@cli.command()
def stdout_stderr():
    sys.stdout.write('this is stdout data\n')
    sys.stderr.write('this is stderr data\n')


@cli.command()
@click.option('-p', type=click.File('w'))
@click.option('--progressions', type=str)
def progress(p, progressions):
    progressions = json.loads(progressions)

    for msg in progressions:
        p.write('%s\n' % json.dumps(msg))
        p.flush()


@cli.command()
@click.option('-i', type=click.File('r'))
@click.option('-o', type=click.File('w'))
def read_write(i, o):
    while True:
        data = i.read(1024)
        if not data:
            break
        o.write(data)


@cli.command()
@click.option('-p', type=str)
def print_path(p):
    print(p)


@cli.command()
def raise_exception():
    raise Exception('girder docker exception')


@cli.command()
@click.option('-d', type=click.Path(dir_okay=True, file_okay=False))
def listdir(d):
    for path in os.listdir(d):
        print(path)


if __name__ == '__main__':
    cli(obj={})
