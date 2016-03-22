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


def _convertPN(value):
    """
    Convert value for DataElement with VR 'PN' (PatientName) to JSON Model
    Object Structure.
    """
    value = str(value)  # In Python 3, pydicom creates PersonName3 object
    groups = value.split('=')
    value = {}
    size = len(groups)
    if groups[0]:
        value['Alphabetic'] = groups[0]
    if size > 1 and groups[1]:
        value['Ideographic'] = groups[1]
    if size > 2 and groups[2]:
        value['Phonetic'] = groups[2]
    if not value:
        value = None
    return value


def _convertSQ(value):
    """
    Convert value for DataElement with VR 'SQ' (Sequence) to JSON Model Object
    Structure.
    """
    return list(map(datasetToJSON, value))


def _convertValue(vr, value):
    if isinstance(value, float) or vr in ('FL', 'FD'):
        value = float(value)
    elif isinstance(value, int) or vr in ('SL', 'SS', 'UL', 'US'):
        value = int(value)
    elif vr == 'PN':
        value = _convertPN(value)
    elif not value:
        value = None
    return value


def dataElementToJSON(dataElement):
    """
    Convert pydicom DataElement to DICOM JSON Model Object Structure.
    See: F.2.2 DICOM JSON Model Object Structure.
    """
    # XXX: Binary VRs, likely incomplete. Add placeholder value for now.
    unsupported = ('OB', 'OD', 'OF', 'OW', 'OB/OW', 'OW/OB', 'OB or OW',
                   'OW or OB', 'UN', 'US or SS')
    # XXX: encode string values as UTF-8?

    tag = dataElement.tag
    vr = dataElement.VR
    value = dataElement.value
    if vr == 'SQ':
        value = _convertSQ(value)
    elif vr in unsupported:
        value = '<BINARY>'
    else:
        if dataElement.VM == 1:
            value = [_convertValue(vr, value)]
        else:
            value = [_convertValue(vr, v) for v in value]

    key = '{:04X}{:04X}'.format(tag.group, tag.element)
    d = {
        'vr': vr
    }
    if any(v is not None for v in value):
        d['Value'] = value

    return {
        key: d
    }


def datasetToJSON(dataset):
    """
    Convert pydicom Dataset to DICOM JSON Model Object Structure.
    See: F.2.2 DICOM JSON Model Object Structure.
    """
    obj = {}
    for dataElement in dataset:
        attrib = dataElementToJSON(dataElement)
        obj.update(attrib)
    return obj
