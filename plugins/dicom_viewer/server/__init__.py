from dicom.sequence import Sequence
from girder import events
from girder.api import access
from girder.api.describe import Description, describeRoute
from girder.api.rest import Resource, loadmodel
from girder.constants import AccessType, TokenScope
from girder.utility.model_importer import ModelImporter
from StringIO import StringIO
import dicom

MAX_FILE_SIZE = 1024 * 1024 * 5


class DicomItem(Resource):

    @access.user(scope=TokenScope.DATA_READ)
    @loadmodel(model='item', level=AccessType.READ)
    @describeRoute(
        Description('Get DICOM metadata, if any, for all files in the item.')
        .param('id', 'The item ID', paramType='path')
        .param('filters', 'Filter returned DICOM tags (comma-separated).', required=False)
        .errorResponse('ID was invalid.')
        .errorResponse('Read permission denied on the item.', 403)
    )
    def getDicom(self, item, params):
        filters = set(filter(None, params.get('filters', '').split(',')))
        files = list(ModelImporter.model('item').childFiles(item))
        # process files if they haven't been processed yet
        for i, file in enumerate(files):
            if 'dicom' not in file:
                files[i] = process_file(file)
        # filter out non-dicom files
        files = [x for x in files if x.get('dicom')]
        # sort files
        files = sorted(files, key=sort_key)
        # execute filters
        if filters:
            for file in files:
                dicom = file['dicom']
                dicom = dict((k, dicom[k]) for k in filters if k in dicom)
                file['dicom'] = dicom
        return files


def sort_key(file):
    dicom = file.get('dicom', {})
    return (
        dicom.get('SeriesNumber'),
        dicom.get('InstanceNumber'),
        dicom.get('SliceLocation'),
        file['name'],
    )


def can_encode(x):
    if isinstance(x, Sequence):
        return False
    if isinstance(x, list):
        return all(can_encode(y) for y in x)
    try:
        unicode(x)
        return True
    except Exception:
        return False


def process_file(file):
    data = {}
    try:
        if file['size'] <= MAX_FILE_SIZE:
            # download file and try to parse dicom
            stream = ModelImporter.model('file').download(file, headers=False)
            fp = StringIO(''.join(stream()))
            ds = dicom.read_file(fp, stop_before_pixels=True)
            # human-readable keys
            for key in ds.dir():
                value = ds.data_element(key).value
                if can_encode(value):
                    data[key] = value
            # hex keys
            for key, value in ds.items():
                key = 'x%04x%04x' % (key.group, key.element)
                value = value.value
                if can_encode(value):
                    data[key] = value
    except Exception:
        pass
    # store dicom data in file
    file['dicom'] = data
    return ModelImporter.model('file').save(file)


def handler(event):
    process_file(event.info['file'])


def load(info):
    events.bind('data.process', 'dicom_viewer', handler)
    dicomItem = DicomItem()
    info['apiRoot'].item.route(
        'GET', (':id', 'dicom'), dicomItem.getDicom)
