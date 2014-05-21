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

import cherrypy
import os
import smtplib

from email.mime.text import MIMEText
from mako.template import Template
from mako.lookup import TemplateLookup
from girder import events
from girder.constants import SettingKey, ROOT_DIR
from . import config
from .model_importer import ModelImporter


def renderTemplate(name, params={}):
    """
    Renders one of the HTML mail templates located in girder/mail_templates.

    :param name: The name of the file inside girder/mail_templates to render.
    :param params: The parameters to pass when rendering the template.
    :type params: dict
    :returns: The rendered template as a string of HTML.
    """
    host = '://'.join((cherrypy.request.scheme, cherrypy.request.local.name))

    if cherrypy.request.local.port != 80:
        host += ':{}'.format(cherrypy.request.local.port)

    params['host'] = host
    template = _templateLookup.get_template(name)
    return template.render(**params)


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
    msg = MIMEText(text, 'html')
    msg['Subject'] = subject
    msg['To'] = to
    msg['From'] = ModelImporter().model('setting').get(
        SettingKey.EMAIL_FROM_ADDRESS, 'no-reply@girder')

    events.daemon.trigger('_sendmail', info=msg)


def addTemplateDirectory(dir):
    """
    Adds a directory to the search path for mail templates. This is useful
    for plugins that have their own set of mail templates.

    :param dir: The directory to add to the template lookup path.
    :type dir: str
    """
    _templateLookup.directories.append(dir)


def _sendmail(event):
    msg = event.info
    s = smtplib.SMTP(
        ModelImporter().model('setting').get(SettingKey.SMTP_HOST, 'localhost'))
    s.sendmail(msg['From'], (msg['To'],), msg.as_string())
    s.quit()


_templateDir = os.path.join(ROOT_DIR, 'girder', 'mail_templates')
_templateLookup = TemplateLookup(directories=[_templateDir], collection_size=50)
events.bind('_sendmail', 'core.email', _sendmail)
