'''
This script is intended to be run after migrating from Midas to Girder.

During migration, Midas items that had multiple "bitstreams" are downloaded as a
zip file and stored in Girder as such. This script looks for zip files that are
flat (have no folders) and have multiple file entries and unzips them into the
same item, removes the zip file, and removes the .zip extension from the item.

In the future, the migration script should be updated to fetch each bitstream
and store them as files, removing the need for this script.
'''

import girder_client
import os
import tempfile
import zipfile

DRY_RUN = False

MAX_ZIP_FILE_SIZE = -1
# MAX_ZIP_FILE_SIZE = 1024 * 1024 * 1024 # 1GB

GIRDER_URL = 'http://127.0.0.1/api/v1'
GIRDER_API_KEY = 'API_KEY'

gc = girder_client.GirderClient(apiUrl=GIRDER_URL)
gc.authenticate(apiKey=GIRDER_API_KEY)

def process_item(item):
    print 'item', item['_id'], item['name']

    # item name should end with ".zip"
    if not item['name'].lower().endswith('.zip'):
        print 'SKIP: item name does not end with ".zip"'
        return False

    # item should have one file
    files = list(gc.listFile(item['_id']))
    if len(files) != 1:
        print 'SKIP: item contains more than one file'
        return False

    f = files[0]
    print 'file', f['_id'], f['name']

    # file name should match item name
    if f['name'] != item['name']:
        print 'SKIP: file name does not match item name'
        return False

    # check zip file size
    if MAX_ZIP_FILE_SIZE >= 0 and f['size'] > MAX_ZIP_FILE_SIZE:
        print 'SKIP: file size too large'
        return False

    # download zip file to temp file
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        print 'DOWNLOAD: %d bytes' % f['size']
        gc.downloadFile(f['_id'], tmp)

    # zip file should have no folders and more than one file
    folders = False
    multiple = True
    with zipfile.ZipFile(tmp.name, 'r') as zf:
        infos = zf.infolist()
        if len(infos) < 2:
            multiple = False
        for info in infos:
            print 'ENTRY: %s' % info.filename
            if '/' in info.filename or '..' in info.filename:
                folders = True
                break
    if not multiple:
        print 'SKIP: zip file does not contain multiple files'
        os.remove(tmp.name)
        return False
    if folders:
        print 'SKIP: zip file contains folders'
        os.remove(tmp.name)
        return False

    # extract and upload files
    print 'EXTRACT'
    d = tempfile.mkdtemp()
    with zipfile.ZipFile(tmp.name, 'r') as zf:
        for info in zf.infolist():
            print 'UPLOAD: %s' % info.filename
            path = zf.extract(info, d)
            if not DRY_RUN:
                gc.uploadFileToItem(item['_id'], path)
            os.remove(path)
    os.rmdir(d)
    os.remove(tmp.name)

    if not DRY_RUN:
        # delete the original zip file
        gc.delete('file/%s' % f['_id'])
        # remove ".zip" from the item name
        gc.put('item/%s' % item['_id'], dict(name=item['name'][:-4]))

    print 'DONE', item['_id'], item['name'][:-4]
    return True

def find_zip_items():
    params = dict(q='zip', types='["item"]', limit=0)
    response = gc.get('resource/search', params)
    return response.get('item', [])

def main():
    items = find_zip_items()
    for item in items:
        process_item(item)
        print

if __name__ == '__main__':
    main()
