# -*- coding: utf-8 -*-
from bson.objectid import ObjectId
import functools
import io
import sys
import traceback
import pydicom
import numpy as np

from girder import events
from girder.models.file import File
from girder.models.upload import Upload
from girder_jobs.constants import JobStatus
from girder_jobs.models.job import Job
from girder.utility.model_importer import ModelImporter
from PIL import Image


def run(job):
    jobModel = Job()
    jobModel.updateJob(job, status=JobStatus.RUNNING)

    try:
        newFile = createThumbnail(**job['kwargs'])
        log = 'Created thumbnail file %s.' % newFile['_id']
        jobModel.updateJob(job, status=JobStatus.SUCCESS, log=log)
    except Exception:
        t, val, tb = sys.exc_info()
        log = '%s: %s\n%s' % (t.__name__, repr(val), traceback.extract_tb(tb))
        jobModel.updateJob(job, status=JobStatus.ERROR, log=log)
        raise


def createThumbnail(width, height, crop, fileId, attachToType, attachToId):
    """
    Creates the thumbnail. Validation and access control must be done prior
    to the invocation of this method.
    """
    fileModel = File()
    file = fileModel.load(fileId, force=True)
    streamFn = functools.partial(fileModel.download, file, headers=False)

    event = events.trigger('thumbnails.create', info={
        'file': file,
        'width': width,
        'height': height,
        'crop': crop,
        'attachToType': attachToType,
        'attachToId': attachToId,
        'streamFn': streamFn
    })

    if len(event.responses):
        resp = event.responses[-1]
        newFile = resp['file']

        if event.defaultPrevented:
            if resp.get('attach', True):
                newFile = attachThumbnail(file, newFile, attachToType, attachToId, width, height)
            return newFile
        else:
            file = newFile
            streamFn = functools.partial(
                fileModel.download, file, headers=False)

    if 'assetstoreId' not in file:
        # TODO we could thumbnail link files if we really wanted.
        raise Exception('File %s has no assetstore.' % fileId)

    stream = streamFn()
    data = b''.join(stream())

    image = _getImage(file['mimeType'], file['exts'], data)

    if not width:
        width = int(height * image.size[0] / image.size[1])
    elif not height:
        height = int(width * image.size[1] / image.size[0])
    elif crop:
        x1 = y1 = 0
        x2, y2 = image.size
        wr = float(image.size[0]) / width
        hr = float(image.size[1]) / height

        if hr > wr:
            y1 = int(y2 / 2 - height * wr / 2)
            y2 = int(y2 / 2 + height * wr / 2)
        else:
            x1 = int(x2 / 2 - width * hr / 2)
            x2 = int(x2 / 2 + width * hr / 2)
        image = image.crop((x1, y1, x2, y2))

    image.thumbnail((width, height), Image.ANTIALIAS)

    out = io.BytesIO()
    image.convert('RGB').save(out, 'JPEG', quality=85)
    size = out.tell()
    out.seek(0)

    thumbnail = Upload().uploadFromFile(
        out, size=size, name='_thumb.jpg', parentType=attachToType,
        parent={'_id': ObjectId(attachToId)}, user=None, mimeType='image/jpeg',
        attachParent=True)

    return attachThumbnail(file, thumbnail, attachToType, attachToId, width, height)


def attachThumbnail(file, thumbnail, attachToType, attachToId, width, height):
    """
    Add the required information to the thumbnail file and the resource it
    is being attached to, and save the documents.

    :param file: The file from which the thumbnail was derived.
    :type file: dict
    :param thumbnail: The newly generated thumbnail file document.
    :type thumbnail: dict
    :param attachToType: The type to which the thumbnail is being attached.
    :type attachToType: str
    :param attachToId: The ID of the document to attach the thumbnail to.
    :type attachToId: str or ObjectId
    :param width: Thumbnail width.
    :type width: int
    :param height: Thumbnail height.
    :type height: int
    :returns: The updated thumbnail file document.
    """
    parentModel = ModelImporter.model(attachToType)
    parent = parentModel.load(attachToId, force=True)
    parent['_thumbnails'] = parent.get('_thumbnails', [])
    parent['_thumbnails'].append(thumbnail['_id'])
    parentModel.save(parent)

    thumbnail['attachedToType'] = attachToType
    thumbnail['attachedToId'] = parent['_id']
    thumbnail['isThumbnail'] = True
    thumbnail['derivedFrom'] = {
        'type': 'file',
        'id': file['_id'],
        'process': 'thumbnail',
        'width': width,
        'height': height
    }

    return File().save(thumbnail)


def _getImage(mimeType, extension, data):
    """
    Check extension of image and opens it.

    :param extension: The extension of the image that needs to be opened.
    :param data: The image file stream.
    """
    if (extension and extension[-1] == 'dcm') or mimeType == 'application/dicom':
        # Open the dicom image
        dicomData = pydicom.dcmread(io.BytesIO(data))
        return scaleDicomLevels(dicomData)
    else:
        # Open other types of images
        return Image.open(io.BytesIO(data))


def scaleDicomLevels(dicomData):
    """
    Adjust dicom levels so image is viewable.

    :param dicomData: The image data to be processed.
    """
    offset = dicomData.RescaleIntercept
    imageData = dicomData.pixel_array
    if len(imageData.shape) == 3:
        minimum = imageData[0].min() + offset
        maximum = imageData[0].max() + offset
        finalImage = _scaleIntensity(imageData[0], maximum - minimum, (maximum + minimum) / 2)
        return Image.fromarray(finalImage).convert('I')
    else:
        minimum = imageData.min() + offset
        maximum = imageData.max() + offset
        finalImage = _scaleIntensity(imageData, maximum - minimum, (maximum + minimum) / 2)
        return Image.fromarray(finalImage).convert('I')


def _scaleIntensity(img, window, level, maxc=255):
    """Change window and level data in image.

    :param img: numpy array representing an image
    :param window: the window for the transformation
    :param level: the level for the transformation
    :param maxc: what the maximum display color is

    """
    m = maxc / (2.0 * window)
    o = m * (level - window)
    return np.clip((m * img - o), 0, maxc).astype(np.uint8)
