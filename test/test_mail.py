# -*- coding: utf-8 -*-
import os

import pytest

from girder.constants import SettingKey
from girder.models.setting import Setting
from girder.models.user import User
from girder.utility import mail_utils
from girder.plugin import GirderPlugin


class MailPlugin(GirderPlugin):
    def load(self, info):
        mail_utils.addTemplateDirectory(
            os.path.join(os.path.dirname(__file__), 'data', 'mail_templates'),
            prepend=True
        )


def testEmailAdmins(smtp):
    assert smtp.isMailQueueEmpty()

    for i in range(2):
        # Create 2 admin users to test sending mail to admins
        User().createUser(
            firstName='Admin%d' % i, lastName='Admin', login='admin%d' % i,
            password='password', admin=True, email='admin%d@admin.com' % i)

    # Set the email from address
    Setting().set(SettingKey.EMAIL_FROM_ADDRESS, 'a@test.com')

    # Test sending email to admin users
    mail_utils.sendEmail(text='hello', toAdmins=True)
    assert smtp.waitForMail()

    message = smtp.getMail(parse=True)
    assert message['subject'] == '[no subject]'
    assert message['content-type'] == 'text/html; charset="utf-8"'
    assert message['to'] == 'admin0@admin.com, admin1@admin.com'
    assert message['from'] == 'a@test.com'
    assert message.get_payload(decode=True) == b'hello'

    # Test sending email to multiple recipients
    assert smtp.isMailQueueEmpty()
    mail_utils.sendEmail(to=('a@abc.com', 'b@abc.com'), text='world', subject='Email alert')
    assert smtp.waitForMail()

    message = smtp.getMail(parse=True)
    assert message['subject'] == 'Email alert'
    assert message['to'] == 'a@abc.com, b@abc.com'
    assert message['from'] == 'a@test.com'
    assert message.get_payload(decode=True) == b'world'

    # Pass nonsense in the "to" field, check exception
    msg = 'You must specify email recipients via "to" or "bcc", or use toAdmins=True.$'
    with pytest.raises(Exception, match=msg):
        mail_utils.sendEmail(text='hello', to=None)


@pytest.mark.plugin('mail_test', MailPlugin)
def testPluginTemplates(server):
    val = 'OVERRIDE CORE FOOTER'
    assert mail_utils.renderTemplate('_footer.mako').strip() == val

    # Make sure it also works from in-mako import statements
    content = mail_utils.renderTemplate('temporaryAccess.mako', {
        'url': 'x'
    })
    assert val in content


def testUnicodeEmail(smtp):
    text = u'Contains unic\xf8de \u0420\u043e\u0441\u0441\u0438\u044f'
    mail_utils.sendEmail(to='fake@fake.com', subject=text, text=text)
    assert smtp.waitForMail()
    message = smtp.getMail(parse=True)
    assert message.get_payload(decode=True) == text.encode('utf8')


def testBcc(smtp):
    bcc = ('a@a.com', 'b@b.com')
    mail_utils.sendEmail(to='first@a.com', bcc=bcc, subject='hi', text='hi')
    assert smtp.waitForMail()
    message = smtp.getMail(parse=True)
    assert message['To'] == 'first@a.com'
    assert message['Bcc'] == ', '.join(bcc)
