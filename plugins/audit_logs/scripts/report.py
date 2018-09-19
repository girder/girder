"""
This script is for creating download reports for a given folder, recursively.

Examples:

    girder shell --plugins=audit_logs report.py -- --folder=57557fac8d777f68be8f3f49 --start-date=2018-09-10T13:55:34.847Z --end-date=2018-09-13T13:55:34.847Z --output report.csv
    girder shell --plugins=audit_logs report.py -- -f 57557fac8d777f68be8f3f49
"""
import click
import csv
import datetime
import dateutil.parser
import sys

from bson.objectid import ObjectId

from girder.models.item import Item
from girder.models.folder import Folder
from girder.constants import AccessType
from girder.plugins.audit_logs import Record


def index_folder(folderId):
    if Folder().load(folderId, force=True) is None:
        raise ValueError('folderId={} was not a valid folder'.format(folderId))
    items = Item().find({'folderId': ObjectId(folderId)})
    subfolders = Folder().find({'parentId': ObjectId(folderId)})

    files = []
    for item in items:
        for file in Item().childFiles(item, fields={'_id': True}):
            fileId = file['_id']
            files.append(fileId)

    for folder in subfolders:
        files += index_folder(folder['_id'])

    return files


def get_file_download_records(files, start=None, end=None):
    query = {
        'type': 'file.download',
        'details.fileId': {
            '$in': files,
        },
        'details.startByte': 0
    }
    if (start is not None) or (end is not None):
        whenClause = {'when': {}}
        if start is not None:
            whenClause['when']['$gte'] = dateutil.parser.parse(start)
        if end is not None:
            whenClause['when']['$lt'] = dateutil.parser.parse(end)
        query.update(whenClause)
    return Record().find(query)


@click.command()
@click.option('-f', '--folder', help='folder ID to use as root for all download reports.', required=True)
@click.option('--start-date', help='ISO 8601 format')
@click.option('--end-date', help='ISO 8601 format')
@click.option('-o', '--output', type=click.File('w'), default=sys.stdout, help='file to write out')
def report(folder, start_date, end_date, output):
    files = index_folder(folder)
    records = get_file_download_records(files, start=start_date, end=end_date)
    fieldnames = ['file_id', 'ip', 'timestamp']
    rows = ({
        'file_id': r['details']['fileId'],
        'ip': r['ip'],
        'timestamp': r['when'].isoformat(),
        } for r in records)
    reportwriter = csv.DictWriter(output, fieldnames=fieldnames)
    reportwriter.writeheader()
    reportwriter.writerows(rows)


if __name__ == '__main__':
    report()
