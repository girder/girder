import email
import os

import pytest

from girder.models.setting import Setting
from girder.models.user import User
from girder.plugin import GirderPlugin
from girder.settings import SettingKey
from girder.utility import mail_utils


class MailPlugin(GirderPlugin):
    def load(self, info):
        mail_utils.addTemplateDirectory(
            os.path.join(os.path.dirname(__file__), 'data', 'mail_templates'),
            prepend=True
        )


def _get_mail_from_stdout(text: str):
    msg = text[text.find('MIME-Version:'):]
    return email.message_from_string(msg)


def testEmailAdmins(email_stdout, capsys):
    for i in range(2):
        # Create 2 admin users to test sending mail to admins
        User().createUser(
            firstName='Admin%d' % i, lastName='Admin', login='admin%d' % i,
            password='password', admin=True, email='admin%d@admin.com' % i)

    # Set the email from address
    Setting().set(SettingKey.EMAIL_FROM_ADDRESS, 'a@girder.test')

    # Test sending email to admin users
    mail_utils.sendMailToAdmins('Notification', 'hello')
    message = _get_mail_from_stdout(capsys.readouterr().out)
    assert message['subject'] == 'Notification'
    assert message['content-type'] == 'text/html; charset="utf-8"'
    assert message['to'] == 'admin0@admin.com, admin1@admin.com'
    assert message['from'] == 'a@girder.test'
    assert message.get_payload(decode=True) == b'hello'

    # Test sending email to multiple recipients
    mail_utils.sendMail('Email alert', 'world', to=['a@abc.com', 'b@abc.com'])
    message = _get_mail_from_stdout(capsys.readouterr().out)

    assert message['subject'] == 'Email alert'
    assert message['to'] == 'a@abc.com, b@abc.com'
    assert message['from'] == 'a@girder.test'
    assert message.get_payload(decode=True) == b'world'

    # Pass empty list in the "to" field, check exception
    msg = 'You must specify email recipients via "to" or "bcc".$'
    with pytest.raises(Exception, match=msg):
        mail_utils.sendMail('alert', 'hello', to=[])


@pytest.mark.plugin('mail_test', MailPlugin)
def testPluginTemplates(server):
    val = 'OVERRIDE CORE FOOTER'
    assert mail_utils.renderTemplate('_footer.mako').strip() == val

    # Make sure it also works from in-mako import statements
    content = mail_utils.renderTemplate('temporaryAccess.mako', {
        'url': 'x'
    })
    assert val in content


def testUnicodeEmail(email_stdout, capsys):
    text = 'Contains unic\xf8de \u0420\u043e\u0441\u0441\u0438\u044f'
    mail_utils.sendMail(text, text, ['fake@fake.com'])
    message = _get_mail_from_stdout(capsys.readouterr().out)
    assert message.get_payload(decode=True) == text.encode('utf8')


def testBcc(email_stdout, capsys):
    bcc = ['a@a.com', 'b@b.com']
    mail_utils.sendMail('hi', 'hi', ['first@a.com'], bcc=bcc)
    message = _get_mail_from_stdout(capsys.readouterr().out)
    assert message['To'] == 'first@a.com'
    assert message['Bcc'] == ', '.join(bcc)


class _FakeSMTP:
    """Records the arguments smtplib would have been constructed with."""

    instances = []

    def __init__(self, host, port, local_hostname=None, timeout=None):
        self.host = host
        self.port = port
        self.local_hostname = local_hostname
        self.timeout = timeout
        self.startedTls = False
        self.loggedIn = None
        _FakeSMTP.instances.append(self)

    def starttls(self):
        self.startedTls = True

    def login(self, username, password):
        self.loggedIn = (username, password)

    def sendmail(self, fromAddress, toAddresses, message):
        pass

    def quit(self):
        pass


@pytest.fixture
def fakeSmtp(monkeypatch):
    _FakeSMTP.instances = []
    monkeypatch.setattr(mail_utils.smtplib, 'SMTP', _FakeSMTP)
    monkeypatch.setattr(mail_utils.smtplib, 'SMTP_SSL', _FakeSMTP)
    yield _FakeSMTP


@pytest.mark.parametrize('encryption,expectTls', [
    ('none', False),
    ('starttls', True),
    ('ssl', False),
])
def testSmtpConnectionPassesTimeoutAndHostname(fakeSmtp, encryption, expectTls):
    # A connection must never be created without a timeout: smtplib would otherwise
    # inherit the global socket default (normally None) and block forever on a
    # submission that is dropped rather than refused.
    with mail_utils._SMTPConnection(
            host='smtp.test', port=587, encryption=encryption,
            localHostname='girder.test'):
        pass

    conn, = fakeSmtp.instances
    assert conn.timeout == mail_utils.SMTP_TIMEOUT
    assert conn.local_hostname == 'girder.test'
    assert conn.startedTls is expectTls
    assert conn.loggedIn is None


def testSmtpConnectionLoginRequiresBoth(fakeSmtp):
    with mail_utils._SMTPConnection(host='smtp.test', port=587, username='u'):
        pass
    assert fakeSmtp.instances[-1].loggedIn is None

    with mail_utils._SMTPConnection(host='smtp.test', port=587, username='u', password='p'):
        pass
    assert fakeSmtp.instances[-1].loggedIn == ('u', 'p')


@pytest.mark.parametrize('emailHost,expected', [
    ('https://girder.test', 'girder.test'),
    ('http://girder.test:8080', 'girder.test'),
    ('', None),
    ('not a url', None),
])
def testLocalHostname(db, emailHost, expected):
    Setting().set(SettingKey.EMAIL_HOST, emailHost)
    assert mail_utils._localHostname() == expected
