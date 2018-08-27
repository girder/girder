"""
This script is for deleting old audit log entries from the database. Due to the relative
import, it should be run from the parent dir as `python -m server.cleanup`. TODO Pip installable
plugins will allow us to just expose a console entry point for this.
"""
import click
import datetime
from . import Record


@click.command()
@click.option('--days', type=click.INT, help='How many days to preserve records', default=90)
@click.option('--types', help='Which record types to remove as a comma separated list. If not '
              'provided, removes all record types.')
def cleanup(days, types):
    filter = {'when': {'$lt': datetime.datetime.utcnow() - datetime.timedelta(days=days)}}

    if types:
        filter['type'] = {'$in': types.split(',')}

    print('Deleted %d log entries.' % Record().collection.delete_many(filter).deleted_count)


if __name__ == '__main__':
    cleanup()
