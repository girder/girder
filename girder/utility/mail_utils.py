# -*- coding: utf-8 -*-
import os
import re
import six
import smtplib

from email.mime.text import MIMEText
from mako.lookup import TemplateLookup
from girder import events
from girder import logger
from girder.constants import PACKAGE_DIR
from girder.settings import SettingKey


def validateEmailAddress(address):
    """
    Determines whether a string is a valid email address.

    This implements the grammar from 4.10.5.1.5 of the HTML Standard.

    :param address: The string to test.
    :type address: str
    :rtype: bool
    """
    # https://html.spec.whatwg.org/multipage/input.html#valid-e-mail-address
    return re.match(
        r'^[a-zA-Z0-9.!#$%&\'*+/=?^_`{|}~-]+'
        r'@[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?'
        r'(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*$',
        address
    ) is not None


def getEmailUrlPrefix():
    """
    Return the URL prefix for links back to the server. This is the link to the
    server root, so Girder-level path information and any query parameters or
    fragment value should be appended to this value.
    """
    from girder.models.setting import Setting
    return Setting().get(SettingKey.EMAIL_HOST)


def renderTemplate(name, params=None):
    """
    Renders one of the HTML mail templates located in girder/mail_templates.

    :param name: The name of the file inside girder/mail_templates to render.
    :param params: The parameters to pass when rendering the template.
    :type params: dict
    :returns: The rendered template as a string of HTML.
    """
    from girder.models.setting import Setting

    if not params:
        params = {}

    if 'host' not in params:
        params['host'] = getEmailUrlPrefix()
    if 'brandName' not in params:
        params['brandName'] = Setting().get(SettingKey.BRAND_NAME)

    template = _templateLookup.get_template(name)
    return template.render(**params)


def sendEmail(to=None, subject=None, text=None, toAdmins=False, bcc=None):
    """
    Send an email. This builds the appropriate email object and then triggers
    an asynchronous event to send the email (handled in _sendmail).

    :param to: The recipient's email address, or a list of addresses.
    :type to: str, list/tuple, or None
    :param subject: The subject line of the email.
    :type subject: str
    :param text: The body of the email.
    :type text: str
    :param toAdmins: To send an email to all site administrators, set this
        to True, which will override any "to" argument that was passed.
    :type toAdmins: bool
    :param bcc: Recipient email address(es) that should be specified using the
        Bcc header.
    :type bcc: str, list/tuple, or None
    """
    from girder.models.setting import Setting
    from girder.models.user import User

    to = to or ()
    bcc = bcc or ()

    if toAdmins:
        to = [u['email'] for u in User().getAdmins()]
    else:
        if isinstance(to, six.string_types):
            to = (to,)
        if isinstance(bcc, six.string_types):
            bcc = (bcc,)

    if not to and not bcc:
        raise Exception('You must specify email recipients via "to" or "bcc", '
                        'or use toAdmins=True.')

    if isinstance(text, six.text_type):
        text = text.encode('utf8')

    msg = MIMEText(text, 'html', 'UTF-8')
    msg['Subject'] = subject or '[no subject]'

    if to:
        msg['To'] = ', '.join(to)
    if bcc:
        msg['Bcc'] = ', '.join(bcc)

    msg['From'] = Setting().get(SettingKey.EMAIL_FROM_ADDRESS)

    events.daemon.trigger('_sendmail', info={
        'message': msg,
        'recipients': list(set(to) | set(bcc))
    })


def addTemplateDirectory(dir, prepend=False):
    """
    Adds a directory to the search path for mail templates. This is useful
    for plugins that have their own set of mail templates.

    :param dir: The directory to add to the template lookup path.
    :type dir: str
    :param prepend: If True, adds this directory at the beginning of the path so
        that it will override any existing templates with the same name.
        Otherwise appends to the end of the lookup path.
    :type prepend: bool
    """
    idx = 0 if prepend else len(_templateLookup.directories)
    _templateLookup.directories.insert(idx, dir)


class _SMTPConnection(object):
    def __init__(self, host, port=None, encryption=None,
                 username=None, password=None):
        self.host = host
        self.port = port
        self.encryption = encryption
        self.username = username
        self.password = password

    def __enter__(self):
        if self.encryption == 'ssl':
            self.connection = smtplib.SMTP_SSL(self.host, self.port)
        else:
            self.connection = smtplib.SMTP(self.host, self.port)
            if self.encryption == 'starttls':
                self.connection.starttls()
        if self.username and self.password:
            self.connection.login(self.username, self.password)
        return self

    def send(self, fromAddress, toAddresses, message):
        self.connection.sendmail(fromAddress, toAddresses, message)

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.connection.quit()


def _sendmail(event):
    from girder.models.setting import Setting

    msg = event.info['message']
    recipients = event.info['recipients']

    setting = Setting()
    smtp = _SMTPConnection(
        host=setting.get(SettingKey.SMTP_HOST),
        port=setting.get(SettingKey.SMTP_PORT),
        encryption=setting.get(SettingKey.SMTP_ENCRYPTION),
        username=setting.get(SettingKey.SMTP_USERNAME),
        password=setting.get(SettingKey.SMTP_PASSWORD)
    )

    logger.info('Sending email to %s through %s', ', '.join(recipients), smtp.host)

    with smtp:
        smtp.send(msg['From'], recipients, msg.as_string())


_templateDir = os.path.join(PACKAGE_DIR, 'mail_templates')
_templateLookup = TemplateLookup(directories=[_templateDir], collection_size=50)
events.bind('_sendmail', 'core.email', _sendmail)
