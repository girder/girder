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

import os

from .. import base
from girder.constants import SettingKey
from girder.utility import config, mail_utils


def setUpModule():
    pluginRoot = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                              'test_plugins')
    conf = config.getConfig()
    conf['plugins'] = {'plugin_directory': pluginRoot}
    base.enabledPlugins.append('mail_test')

    base.startServer()


def tearDownModule():
    base.stopServer()


class MailTestCase(base.TestCase):
    """
    Test the email utilities.
    """

    def testEmailAdmins(self):
        self.assertTrue(base.mockSmtp.isMailQueueEmpty())

        admin1, admin2 = [self.model('user').createUser(
            firstName='Admin%d' % i, lastName='Admin', login='admin%d' % i,
            password='password', admin=True, email='admin%d@admin.com' % i)
            for i in range(2)]

        # Set the email from address
        self.model('setting').set(SettingKey.EMAIL_FROM_ADDRESS, 'a@test.com')

        # Test sending email to admin users
        mail_utils.sendEmail(text='hello', toAdmins=True)
        self.assertTrue(base.mockSmtp.waitForMail())

        message = base.mockSmtp.getMail(parse=True)
        self.assertEqual(message['subject'], '[no subject]')
        self.assertEqual(message['content-type'], 'text/html; charset="utf-8"')
        self.assertEqual(message['to'], 'admin0@admin.com, admin1@admin.com')
        self.assertEqual(message['from'], 'a@test.com')
        self.assertEqual(message.get_payload(decode=True), b'hello')

        # Test sending email to multiple recipients
        self.assertTrue(base.mockSmtp.isMailQueueEmpty())
        mail_utils.sendEmail(to=('a@abc.com', 'b@abc.com'), text='world',
                             subject='Email alert')
        self.assertTrue(base.mockSmtp.waitForMail())

        message = base.mockSmtp.getMail(parse=True)
        self.assertEqual(message['subject'], 'Email alert')
        self.assertEqual(message['to'], 'a@abc.com, b@abc.com')
        self.assertEqual(message['from'], 'a@test.com')
        self.assertEqual(message.get_payload(decode=True), b'world')

        # Pass nonsense in the "to" field, check exception
        x = 0
        try:
            mail_utils.sendEmail(text='hello', to=None)
        except Exception as e:
            x = 1
            self.assertEqual(
                e.args[0], 'You must specify email recipients via "to" or '
                '"bcc", or use toAdmins=True.')

        self.assertEqual(x, 1)

    def testPluginTemplates(self):
        val = 'OVERRIDE CORE FOOTER'
        self.assertEqual(mail_utils.renderTemplate('_footer.mako').strip(), val)

        # Make sure it also works from in-mako import statements
        content = mail_utils.renderTemplate('temporaryAccess.mako', {
            'url': 'x'
        })
        self.assertTrue(val in content)

    def testUnicodeEmail(self):
        text = u'Contains unic\xf8de \u0420\u043e\u0441\u0441\u0438\u044f'
        mail_utils.sendEmail(to='fake@fake.com', subject=text, text=text)
        self.assertTrue(base.mockSmtp.waitForMail())
        message = base.mockSmtp.getMail(parse=True)
        self.assertEqual(message.get_payload(decode=True), text.encode('utf8'))

    def testBcc(self):
        bcc = ('a@a.com', 'b@b.com')
        mail_utils.sendEmail(to='first@a.com', bcc=bcc, subject='hi', text='hi')
        self.assertTrue(base.mockSmtp.waitForMail())
        message = base.mockSmtp.getMail(parse=True)
        self.assertEqual(message['To'], 'first@a.com')
        self.assertEqual(message['Bcc'], ', '.join(bcc))
