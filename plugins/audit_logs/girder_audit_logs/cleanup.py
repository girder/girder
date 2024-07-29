"""
This script is for deleting old audit log entries from the database. Example invocation:

    girder audit-logs-cleanup --days=30 --types=rest.request
"""

import click
import datetime
from girder_audit_logs import Record


@click.command(name='audit-logs-cleanup')
@click.option('--days', type=click.INT, help='How many days to preserve records', default=90)
@click.option('--types', help='Which record types to remove as a comma separated list. If not '
              'provided, removes all record types.')
def cleanup(days, types):
    filter = {
        'when': {
            '$lt': datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=days)
        }
    }

    if types:
        filter['type'] = {'$in': types.split(',')}

    click.echo('Deleted %d log entries.' % Record().collection.delete_many(filter).deleted_count)


if __name__ == '__main__':
    cleanup()
