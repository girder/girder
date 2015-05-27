#!/usr/bin/env python
# -*- coding: utf-8 -*-

###############################################################################
#  Copyright Kitware Inc.
#
#  Licensed under the Apache License, Version 2.0 ( the "License" );
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
###############################################################################

import six
import sys
import traceback

from girder.plugins.jobs.constants import JobStatus
from girder.utility.model_importer import ModelImporter
from PIL import Image


def run(job):
    jobModel = ModelImporter.model('job', 'jobs')
    jobModel.updateJob(job, status=JobStatus.RUNNING)

    try:
        newFile = createThumbnail(**job['kwargs'])
        log = 'Created thumbnail file %s.' % newFile['_id']
        jobModel.updateJob(job, status=JobStatus.SUCCESS, log=log)
    except Exception:
        t, val, tb = sys.exc_info()
        log = '%s: %s\n%s' % (t.__name__, repr(val), traceback.extract_tb(tb))
        jobModel.updateJob(job, status=JobStatus.ERROR, log=log)


def createThumbnail(width, height, crop, fileId, attachToType, attachToId):
    """
    Creates the thumbnail. Validation and access control must be done prior
    to the invocation of this method.
    """
    file = ModelImporter.model('file').load(fileId)

    if 'assetstoreId' not in file:
        # TODO we could thumbnail link files if we really wanted.
        raise Exception('File %s has no assetstore.' % fileId)

    stream = ModelImporter.model('file').download(file, headers=False)

    data = ''.join(stream())
    image = Image.open(six.StringIO(data))

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

    return _uploadThumbnail(image, attachToType, attachToId)


def _uploadThumbnail(image, attachToType, attachToId):
    target = ModelImporter.model(attachToType).load(attachToId, force=True)
    uploadModel = ModelImporter.model('upload')

    out = six.BytesIO()
    image.save(out, 'JPEG', quality=75)
    contents = out.getvalue()
    out.close()
    upload = uploadModel.createUpload(
        user=None, name='_thumb.jpg', parentType=None, parent=None,
        size=len(contents), mimeType='image/jpeg')

    file = uploadModel.handleChunk(upload, contents)

    print(file)
    return file
