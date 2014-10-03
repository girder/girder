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

import datetime
import time

from .model_importer import ModelImporter
from girder.models.notification import ProgressState


class ProgressContext(ModelImporter):
    """
    This class is a context manager that can be used to update progress in a way
    that rate-limits writes to the database and guarantees a flush when the
    context is exited.
    """
    def __init__(self, on, interval=0.5, **kwargs):
        """
        Create a new progress manager. This is a no-op if "on" is set to false,
        which is convenient for the caller's semantics.

        :param on: Whether to record progress.
        :type on: bool
        :param interval: Minimum time interval at which to write updates
        to the database, in seconds.
        :type interval: int or float
        """
        self.on = on
        self.interval = interval

        if on:
            self._lastSave = time.time()
            self.progress = self.model('notification').initProgress(**kwargs)

    def __enter__(self):
        return self

    def __exit__(self, excType, excValue, traceback):
        """
        Once the context is exited, the progress is marked for deletion 30
        seconds in the future, which should give all listeners time to poll and
        receive the final state of the progress record before it is deleted.
        """
        if not self.on:
            return

        if excType is None and excValue is None:
            state = ProgressState.SUCCESS
            message = 'Done'
        else:
            state = ProgressState.ERROR
            message = 'Error'

        self.model('notification').updateProgress(
            self.progress, state=state, message=message,
            expires=datetime.datetime.utcnow() + datetime.timedelta(seconds=30)
        )

    def update(self, force=False, **kwargs):
        """
        Update the underlying progress record. This will only actually save
        to the database if at least self.interval seconds have passed since
        the last time the record was written to the database. Accepts the
        same kwargs as Notification.updateProgress.

        :param force: Whether we should force the write to the database.
        Use only in cases where progress may be indeterminate for a long time.
        :type force: bool
        """
        if not self.on:
            return

        save = time.time() - self._lastSave > self.interval
        self.progress = self.model('notification').updateProgress(
            self.progress, save, **kwargs)

        if save:
            self._lastSave = time.time()


noProgress = ProgressContext(False)
