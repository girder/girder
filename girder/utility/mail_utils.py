#!/usr/bin/env python
# -*- coding: utf-8 -*-

###############################################################################
#  Copyright 2014 Kitware Inc.
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

import smtplib

from email.mime.text import MIMEText
from .. import events
from ..constants import SettingKey
from . import config
from .model_importer import ModelImporter


def sendEmail(to, subject, text):
    """
    Send an email. This builds the appropriate email object and then triggers
    an asynchronous event to send the email (handled in _sendmail).

    :param to: The recipient's email address.
    :type to: str
    :param subject: The subject line of the email.
    :type subject: str
    :param text: The body of the email.
    :type text: str
    """
    if config.getConfig()['server']['mode'] == 'production':
        msg = MIMEText(text)
        msg['Subject'] = subject
        msg['To'] = to
        msg['From'] = _settings.get(
            SettingKey.EMAIL_FROM_ADDRESS, 'no-reply@girder')

        events.daemon.trigger('_sendmail', info=msg)


def _sendmail(event):
    msg = event.info
    s = smtplib.SMTP(_settings.get(SettingKey.SMTP_HOST, 'localhost'))
    s.sendmail(msg['From'], (msg['To'],), msg.as_string())
    s.quit()


_settings = ModelImporter().model('setting')
events.bind('_sendmail', 'core.email', _sendmail)
