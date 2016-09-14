#!/usr/bin/env python
# -*- coding: utf-8 -*-

###############################################################################
#  Copyright 2016 Kitware Inc.
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

from girder.api import access
from girder.api.describe import Description, describeRoute
from girder.api.rest import Resource, loadmodel, RestException
from girder.constants import AccessType, TokenScope
from girder.utility import mail_utils
from girder.utility.progress import ProgressContext
import datetime


CURATION = 'curation'

ENABLED = 'enabled'
STATUS = 'status'
TIMELINE = 'timeline'
ENABLE_USER_ID = 'enableUserId'
REQUEST_USER_ID = 'requestUserId'
REVIEW_USER_ID = 'reviewUserId'

CONSTRUCTION = 'construction'
REQUESTED = 'requested'
APPROVED = 'approved'

DEFAULTS = {
    ENABLED: False,
    STATUS: CONSTRUCTION,
}

TITLE_PUBLIC = 'Making curated folder public...'
TITLE_PRIVATE = 'Making curated folder private...'
TITLE_WRITEABLE = 'Making curated folder writeable...'
TITLE_READ_ONLY = 'Making curated folder read-only...'


class CuratedFolder(Resource):

    @access.user(scope=TokenScope.DATA_READ)
    @loadmodel(model='folder', level=AccessType.READ)
    @describeRoute(
        Description('Get curation details for the folder.')
        .param('id', 'The folder ID', paramType='path')
        .errorResponse('ID was invalid.')
        .errorResponse('Read permission denied on the folder.', 403)
    )
    def getCuration(self, folder, params):
        result = dict(DEFAULTS)
        result[TIMELINE] = []
        result.update(folder.get(CURATION, {}))
        result['public'] = folder.get('public')
        return result

    @access.user(scope=TokenScope.DATA_WRITE)
    @loadmodel(model='folder', level=AccessType.WRITE)
    @describeRoute(
        Description('Set curation details for the folder.')
        .param('id', 'The folder ID', paramType='path')
        .param('enabled', 'Enable or disable folder curation.',
               required=False, dataType='boolean')
        .param('status', 'Set the folder curation status.',
               required=False, dataType='string',
               enum=[CONSTRUCTION, REQUESTED, APPROVED])
        .errorResponse('ID was invalid.')
        .errorResponse('Write permission denied on the folder.', 403)
    )
    def setCuration(self, folder, params):
        user = self.getCurrentUser()
        if CURATION not in folder:
            folder[CURATION] = dict(DEFAULTS)
        curation = folder[CURATION]
        oldCuration = dict(curation)

        # update enabled
        oldEnabled = curation.get(ENABLED, False)
        if ENABLED in params:
            self.requireAdmin(user)
            curation[ENABLED] = self.boolParam(ENABLED, params)
        enabled = curation.get(ENABLED, False)

        # update status
        oldStatus = curation.get(STATUS)
        if STATUS in params:
            # verify valid status
            if params[STATUS] not in [CONSTRUCTION, REQUESTED, APPROVED]:
                raise RestException('Invalid status parameter')
            # regular users can only do construction -> requested transition
            if curation.get(STATUS) != CONSTRUCTION or \
               params[STATUS] != REQUESTED:
                self.requireAdmin(user)
            curation[STATUS] = params[STATUS]
        status = curation.get(STATUS)

        # admin enabling curation
        if enabled and not oldEnabled:
            # TODO: check if writers exist?
            # TODO: email writers?
            with self._progressContext(folder, TITLE_PRIVATE) as pc:
                self._setPublic(folder, False, pc)
            curation[ENABLE_USER_ID] = user.get('_id')
            self._addTimeline(oldCuration, curation, 'enabled curation')

        # admin reopening folder
        if enabled and oldStatus == APPROVED and status == CONSTRUCTION:
            with self._progressContext(folder, TITLE_PRIVATE) as pc:
                self._setPublic(folder, False, pc)
            curation[ENABLE_USER_ID] = user.get('_id')
            with self._progressContext(folder, TITLE_WRITEABLE) as pc:
                self._makeWriteable(folder, pc)
            self._addTimeline(oldCuration, curation, 'reopened folder')

        # admin disabling curation
        if not enabled and oldEnabled:
            self._addTimeline(oldCuration, curation, 'disabled curation')

        # user requesting approval
        if enabled and oldStatus == CONSTRUCTION and status == REQUESTED:
            curation[REQUEST_USER_ID] = user.get('_id')
            with self._progressContext(folder, TITLE_READ_ONLY) as pc:
                self._makeReadOnly(folder, pc)
            self._addTimeline(oldCuration, curation, 'requested approval')
            # send email to admin requesting approval
            self._sendMail(
                folder, curation.get(ENABLE_USER_ID),
                'REQUEST FOR APPROVAL: ' + folder['name'],
                'curation.requested.mako')

        # admin approving request
        if enabled and oldStatus == REQUESTED and status == APPROVED:
            with self._progressContext(folder, TITLE_PUBLIC) as pc:
                self._setPublic(folder, True, pc)
            curation[REVIEW_USER_ID] = user.get('_id')
            self._addTimeline(oldCuration, curation, 'approved request')
            # send approval notification to requestor
            self._sendMail(
                folder, curation.get(REQUEST_USER_ID),
                'APPROVED: ' + folder['name'],
                'curation.approved.mako')

        # admin rejecting request
        if enabled and oldStatus == REQUESTED and status == CONSTRUCTION:
            curation[REVIEW_USER_ID] = user.get('_id')
            with self._progressContext(folder, TITLE_WRITEABLE) as pc:
                self._makeWriteable(folder, pc)
            self._addTimeline(oldCuration, curation, 'rejected request')
            # send rejection notification to requestor
            self._sendMail(
                folder, curation.get(REQUEST_USER_ID),
                'REJECTED: ' + folder['name'],
                'curation.rejected.mako')

        folder = self.model('folder').save(folder)
        curation['public'] = folder.get('public')
        return curation

    def _progressContext(self, folder, title):
        user = self.getCurrentUser()
        total = self.model('folder').subtreeCount(folder, includeItems=False)
        return ProgressContext(True, user=user, total=total, title=title)

    def _setPublic(self, folder, public, pc):
        """
        Recursively updates folder's public setting.
        """
        pc.update(increment=1)
        folder['public'] = public
        folder = self.model('folder').save(folder)
        subfolders = self.model('folder').find({
            'parentId': folder['_id'],
            'parentCollection': 'folder'
        })
        for folder in subfolders:
            self._setPublic(folder, public, pc)

    def _makeReadOnly(self, folder, pc):
        """
        Recursively updates folder permissions so that anyone with write access
        now has read-only access.
        """
        pc.update(increment=1)
        for doc in folder['access']['users'] + folder['access']['groups']:
            if doc['level'] == AccessType.WRITE:
                doc['level'] = AccessType.READ
        folder = self.model('folder').save(folder)
        subfolders = self.model('folder').find({
            'parentId': folder['_id'],
            'parentCollection': 'folder'
        })
        for folder in subfolders:
            self._makeReadOnly(folder, pc)

    def _makeWriteable(self, folder, pc):
        """
        Recursively updates folder permissions so that anyone with read access
        now has write access.
        """
        pc.update(increment=1)
        for doc in folder['access']['users'] + folder['access']['groups']:
            if doc['level'] == AccessType.READ:
                doc['level'] = AccessType.WRITE
        folder = self.model('folder').save(folder)
        subfolders = self.model('folder').find({
            'parentId': folder['_id'],
            'parentCollection': 'folder'
        })
        for folder in subfolders:
            self._makeWriteable(folder, pc)

    def _addTimeline(self, oldCuration, curation, text):
        """
        Adds a new entry to the curation timeline.

        :param oldCuration: the curation values before the last change
        :param curation: the curation values after the last change
        :param text: a short human-readable description of the change
        """
        user = self.getCurrentUser()
        data = dict(
            userId=user.get('_id'),
            userLogin=user.get('login'),
            text=text,
            oldEnabled=oldCuration[ENABLED],
            oldStatus=oldCuration[STATUS],
            enabled=curation[ENABLED],
            status=curation[STATUS],
            timestamp=datetime.datetime.utcnow())
        curation.setdefault(TIMELINE, []).append(data)

    def _getEmail(self, userId):
        """
        Loads and returns the email address for the specified user.
        """
        return self.model('user').load(userId, force=True).get('email')

    def _sendMail(self, folder, userId, subject, template):
        """
        Sends the specified email template to a single user.

        :param folder: the curated folder
        :param userId: the id of the user to email
        :param subject: the email subject
        :param template: the name of the mako template to use
        """
        if not userId:
            return
        data = dict(
            folder=folder,
            curation=folder[CURATION])
        text = mail_utils.renderTemplate(template, data)
        emails = [self._getEmail(userId)]
        mail_utils.sendEmail(emails, subject, text)


def load(info):
    curatedFolder = CuratedFolder()
    info['apiRoot'].folder.route(
        'GET', (':id', 'curation'), curatedFolder.getCuration)
    info['apiRoot'].folder.route(
        'PUT', (':id', 'curation'), curatedFolder.setCuration)
