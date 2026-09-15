import logging
import os
import re
import smtplib
import urllib.parse
from email.mime.text import MIMEText

from mako.lookup import TemplateLookup

from girder import events
from girder.constants import PACKAGE_DIR
from girder.settings import SettingKey

logger = logging.getLogger(__name__)

# Socket timeout (seconds) for SMTP connections. Without an explicit value smtplib
# inherits the global socket default, which is normally ``None``, potentially blocking
# server thread forever if connection is silently dropped in transit.
# Explicit timeout results in error that we can handle instead
SMTP_TIMEOUT = 30


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


_templateDir = os.path.join(PACKAGE_DIR, 'mail_templates')
_templateLookup = TemplateLookup(directories=[_templateDir], collection_size=50)


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


def _createMessage(subject, text, to, bcc):
    from girder.models.setting import Setting

    # Coerce and validate arguments
    if isinstance(to, str):
        to = [to]
    if isinstance(bcc, str):
        bcc = [bcc]
    elif bcc is None:
        bcc = []
    if not to and not bcc:
        raise Exception('You must specify email recipients via "to" or "bcc".')

    if not subject:
        subject = '[no subject]'

    if isinstance(text, str):
        # TODO: needed?
        text = text.encode('utf8')

    # Build message
    msg = MIMEText(text, 'html', 'UTF-8')
    if to:
        msg['To'] = ', '.join(to)
    if bcc:
        msg['Bcc'] = ', '.join(bcc)
    msg['Subject'] = subject
    msg['From'] = Setting().get(SettingKey.EMAIL_FROM_ADDRESS)

    # Compute recipients
    recipients = list(set(to) | set(bcc))

    return msg, recipients


def _localHostname():
    """
    Return the name to announce in the SMTP EHLO, or None to let smtplib choose.

    Derived from the ``core.email_host`` setting, which already names this instance as
    the outside world sees it. Without one, smtplib falls back to ``socket.getfqdn()``,
    which inside a container typically cannot resolve a real name and yields a bracketed
    address literal leaking the container's private address in every message.
    """
    from girder.models.setting import Setting

    host = Setting().get(SettingKey.EMAIL_HOST)
    if not host:
        return None
    return urllib.parse.urlparse(host).hostname or None


class _SMTPConnection:
    def __init__(self, host, port=None, encryption=None, username=None, password=None,
                 timeout=SMTP_TIMEOUT, localHostname=None):
        self.host = host
        self.port = port
        self.encryption = encryption
        self.username = username
        self.password = password
        self.timeout = timeout
        self.localHostname = localHostname

    def __enter__(self):
        kwargs = {'local_hostname': self.localHostname, 'timeout': self.timeout}
        if self.encryption == 'ssl':
            self.connection = smtplib.SMTP_SSL(self.host, self.port, **kwargs)
        else:
            self.connection = smtplib.SMTP(self.host, self.port, **kwargs)
            if self.encryption == 'starttls':
                self.connection.starttls()
        if self.username and self.password:
            self.connection.login(self.username, self.password)
        return self

    def send(self, fromAddress, toAddresses, message):
        self.connection.sendmail(fromAddress, toAddresses, message)

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.connection.quit()


def _submitEmail(msg, recipients):
    from girder.models.setting import Setting

    if os.environ.get('GIRDER_EMAIL_TO_CONSOLE'):
        print('Redirecting email to console:')
        print(msg.as_string())
        return

    setting = Setting()
    smtp = _SMTPConnection(
        host=setting.get(SettingKey.SMTP_HOST),
        port=setting.get(SettingKey.SMTP_PORT),
        encryption=setting.get(SettingKey.SMTP_ENCRYPTION),
        username=setting.get(SettingKey.SMTP_USERNAME),
        password=setting.get(SettingKey.SMTP_PASSWORD),
        localHostname=_localHostname()
    )

    logger.info('Sending email to %s through %s', ', '.join(recipients), smtp.host)

    with smtp:
        smtp.send(msg['From'], recipients, msg.as_string())


def _sendmail(event):
    msg = event.info['message']
    recipients = event.info['recipients']
    _submitEmail(msg, recipients)


events.bind('_sendmail', 'core.email', _sendmail)


def sendMail(subject, text, to, bcc=None):
    """
    Send an email.

    :param subject: The subject line of the email.
    :type subject: str
    :param text: The body of the email.
    :type text: str
    :param to: The list of recipient email addresses.
    :type to: list
    :param bcc: Recipient email addresses that should be specified using the Bcc header.
    :type bcc: list or None
    """
    msg, recipients = _createMessage(subject, text, to, bcc)

    events.trigger('_sendmail', info={
        'message': msg,
        'recipients': recipients
    })


def sendMailToAdmins(subject, text):
    """Send an email to site admins."""
    from girder.models.user import User

    to = [u['email'] for u in User().getAdmins()]
    sendMail(subject, text, to)


def sendMailIndividually(subject, text, to):
    """Send emails to all recipients individually."""
    for address in to:
        sendMail(address, subject, text)
