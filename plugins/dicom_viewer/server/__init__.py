from dicom.sequence import Sequence
from dicom.valuerep import PersonName3
from girder import events
from girder.api import access
from girder.api.describe import Description, describeRoute
from girder.api.rest import Resource, loadmodel
from girder.constants import AccessType, TokenScope
from girder.utility.model_importer import ModelImporter
import dicom
import six

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
        for i, f in enumerate(files):
            if 'dicom' not in f:
                files[i] = process_file(f)
        # filter out non-dicom files
        files = [x for x in files if x.get('dicom')]
        # sort files
        files = sorted(files, key=sort_key)
        # execute filters
        if filters:
            for f in files:
                dicom = f['dicom']
                dicom = dict((k, dicom[k]) for k in filters if k in dicom)
                f['dicom'] = dicom
        return files


def sort_key(f):
    dicom = f.get('dicom', {})
    return (
        dicom.get('SeriesNumber'),
        dicom.get('InstanceNumber'),
        dicom.get('SliceLocation'),
        f['name'],
    )


def coerce(x):
    if isinstance(x, Sequence):
        return None
    if isinstance(x, list):
        return [coerce(y) for y in x]
    if isinstance(x, PersonName3):
        return x.encode('utf-8')
    try:
        six.text_type(x)
        return x
    except Exception:
        return None


def process_file(f):
    data = {}
    try:
        if f['size'] <= MAX_FILE_SIZE:
            # download file and try to parse dicom
            stream = ModelImporter.model('file').download(f, headers=False)
            fp = six.BytesIO(b''.join(stream()))
            ds = dicom.read_file(fp, stop_before_pixels=True)
            # human-readable keys
            for key in ds.dir():
                value = coerce(ds.data_element(key).value)
                if value is not None:
                    data[key] = value
            # hex keys
            for key, value in ds.items():
                key = 'x%04x%04x' % (key.group, key.element)
                value = coerce(value.value)
                if value is not None:
                    data[key] = value
    except Exception:
        pass
    # store dicom data in file
    f['dicom'] = data
    return ModelImporter.model('file').save(f)


def handler(event):
    process_file(event.info['file'])


def load(info):
    events.bind('data.process', 'dicom_viewer', handler)
    dicomItem = DicomItem()
    info['apiRoot'].item.route(
        'GET', (':id', 'dicom'), dicomItem.getDicom)
