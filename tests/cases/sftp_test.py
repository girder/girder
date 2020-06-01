# -*- coding: utf-8 -*-
import paramiko
import io
import socket
import stat
import threading

from .. import base
from girder.api import sftp
from girder.models.collection import Collection
from girder.models.folder import Folder
from girder.models.upload import Upload
from girder.models.user import User

server = None
TEST_PORT = 10551
TEST_KEY = paramiko.RSAKey.from_private_key(io.StringIO("""-----BEGIN RSA PRIVATE KEY-----
MIIEpAIBAAKCAQEAwdH5tlaZu52adYvW57DcAFknzOKX8+/axDmQdTcg1HwEOnT2
TMSFGciwUQMmya+0i23ZOUtZQutj8fb66szrBZ7qpIvSG6TRyxGuM6PkfAUcBCHO
TGFzaJPnnvUXC8dlxoUIdBaUCmSblvj2q2CTNy53ybAmiiSpahjvBO16pvjbNn+i
EGucSQn71OTMhoSOWtS/VcJC6JPd6kxSdl1EiESbOrjAdNDKMBnfYCkxPG4ulAqe
y5jpfgQiUC0Q3CoWbj/ybAv73JsFndPcpvI8n5EsXeptuWI4CXSorYOuVwURLuzP
z1PkI4ZsYnSnuQG/GReAZnwVDaVJ/uhYMMs1sQIDAQABAoIBADKOmguFBW7aCntU
8cbX7Fsu5mHcTXS1ASSkO1lH+wlSHCw/bCvUKz/xiIRpRQnhCkBAdCQs0mjRS+3G
1ea/cyKxNFWdnz3UvWCyCPWxb50mHAu74bssxFToF8fv+IX7CkJBW1YkuZMIcUlt
QbKsa1o+hcKXb0YjkAl73YU0iQTaet7B1x1X0qkVPEWWURTg3z65TNI96t8p28dh
4HgEoU0Jtfsfzb7u1H4/m3Q28J1S+cTkER/VIgLzMeYXr2MooIQc3QAMXATpXkhM
y6u0LYh+kW1XD4ZnyzTp49BMf76rS8VhsYN6f+jLhJUf/5O+m8NFGuCq15TFyQAH
vMBxPRECgYEA4+fxYuuOq+SilYpejD4EMwvrClixHOfTojlnAyUaJZSnyVp/Y4l+
QmFmbNpfRKN1fv24e9f9CmA8nd5A3kxBjJFhzaaxbFG+jI47fqOu9NadXPHaxvyq
BI2aHx4sqp/Z/ct/klht5hxD8UFMRFbaaLYAojKg1nL0g/88wwwN9LUCgYEA2bZh
873OGT7sNXHin2rXD5XEYXqjLy51hed4ZdtJXFrKhg8ozWqaOZ79GXustdRanzTV
zDeTweI0hg7adbKyBNeuQF8VSOK6ws2wPPCuUbQTVYaepqPuT+VhzAB1GVJ1uF/T
YxgqXOvg9QwnZ4Fjlv3b/52R89bTP+Yr6GcQdo0CgYAvLQ38igIodtVo2xGjOhso
bekjZSSUdTCLvhIixoVZDiKFPaRs+EMYfozzL2jVDnj95otPp3ALu8wQabdHzMUs
0dNK/JxxbaJh+fc6yasnp10/phjBY//VnXIvytE4KIq5TGyF4KQvI960i+27n7bq
QfJzoMNGYNlYkXcEcPRamQKBgQCVCYWElirAnZKWA6BgAYO3547ILGwJoIRTZmHF
WJif4IdDvpzwAkoRqAUbrM5Oq1BeLI0vf9xmnbPXEdP7PpkfN4bSCkVH3+557NT4
4spypBOYOM/iw9YgW6bXQHjpHMn5rZ/H9oMJmXAmUGupL6o9cwtnsTZ49lcnJypn
riZXAQKBgQCgiJ/A11HX7fUgFzBB9no2Sy1hS3u1Ld35nZf7RDegVoEn/UdWdOxn
H2T9t0EzIoSqkfPRrsqN8sv/TMIohS6frOpBojEvwUs5mxjVwswq/QgBSV2FqYck
VeccLgZzTSMNzCDMbtM+zGG5WktzFojrMIhfD0SM3CB3jECF+Dfdtg==
-----END RSA PRIVATE KEY-----
"""))


def setUpModule():
    global server
    server = sftp.SftpServer(('localhost', TEST_PORT), TEST_KEY)
    serverThread = threading.Thread(target=server.serve_forever)
    serverThread.daemon = True
    serverThread.start()


def tearDownModule():
    if server:
        server.shutdown()
        server.server_close()
    base.dropAllTestDatabases()


class SftpTestCase(base.TestCase):
    def testSftpService(self):
        users = ({
            'email': 'admin@girder.test',
            'login': 'admin',
            'firstName': 'First',
            'lastName': 'Last',
            'password': 'passwd'
        }, {
            'email': 'regularuser@girder.test',
            'login': 'regularuser',
            'firstName': 'First',
            'lastName': 'Last',
            'password': 'passwd'
        })

        admin, user = [User().createUser(**user) for user in users]

        collections = ({
            'name': 'public collection',
            'public': True,
            'creator': admin
        }, {
            'name': 'private collection',
            'public': False,
            'creator': admin
        })

        privateFolder = Folder().findOne({
            'parentCollection': 'user',
            'parentId': user['_id'],
            'name': 'Private'
        })
        self.assertIsNotNone(privateFolder)

        Upload().uploadFromFile(
            io.BytesIO(b'hello world'), size=11, name='test.txt', parentType='folder',
            parent=privateFolder, user=user)

        for coll in collections:
            Collection().createCollection(**coll)

        client = paramiko.SSHClient()
        client.load_system_host_keys()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        # Incorrect password should raise authentication error
        with self.assertRaises(paramiko.AuthenticationException):
            client.connect(
                'localhost', TEST_PORT, username='admin', password='badpass', look_for_keys=False,
                allow_agent=False)

        # Authenticate as admin
        client.connect(
            'localhost', TEST_PORT, username='admin', password='passwd', look_for_keys=False,
            allow_agent=False)
        sftpClient = client.open_sftp()
        self.assertEqual(sftpClient.listdir('/'), ['collection', 'user'])

        # Listing an invalid top level entity should fail
        with self.assertRaises(IOError):
            sftpClient.listdir('/foo')

        # Test listing of users, collections, and subfolders
        self.assertEqual(set(sftpClient.listdir('/user/')), {'admin', 'regularuser'})
        self.assertEqual(set(sftpClient.listdir('/user/admin')), {'Public', 'Private'})
        self.assertEqual(
            set(sftpClient.listdir('/collection')), {'public collection', 'private collection'})

        self.assertEqual(sftpClient.listdir('/user/regularuser/Private'), ['test.txt'])
        self.assertEqual(sftpClient.listdir('/user/regularuser/Private/test.txt'), ['test.txt'])

        with self.assertRaisesRegex(IOError, 'No such file'):
            sftpClient.listdir('/user/nonexistent')

        with self.assertRaisesRegex(IOError, 'No such file'):
            sftpClient.file('/user/regularuser/Private')

        # Read a file using small enough buf size to require multiple chunks internally.
        file = sftpClient.file('/user/regularuser/Private/test.txt/test.txt', 'r', bufsize=4)
        self.assertEqual(file.read(2), b'he')
        self.assertEqual(file.read(), b'llo world')

        # Make sure we enforce max buffer length
        tmp, sftp.MAX_BUF_LEN = sftp.MAX_BUF_LEN, 2
        file = sftpClient.file('/user/regularuser/Private/test.txt/test.txt', 'r', bufsize=4)
        with self.assertRaises(IOError):
            file.read()
        sftp.MAX_BUF_LEN = tmp

        # Test stat capability
        info = sftpClient.stat('/user/regularuser/Private')
        self.assertTrue(stat.S_ISDIR(info.st_mode))
        self.assertFalse(stat.S_ISREG(info.st_mode))
        self.assertEqual(info.st_mode & 0o777, 0o777)

        # lstat should also work
        info = sftpClient.lstat('/user/regularuser/Private/test.txt/test.txt')
        self.assertFalse(stat.S_ISDIR(info.st_mode))
        self.assertTrue(stat.S_ISREG(info.st_mode))
        self.assertEqual(info.st_size, 11)
        self.assertEqual(info.st_mode & 0o777, 0o777)

        # File stat implementations should agree
        info = file.stat()
        self.assertFalse(stat.S_ISDIR(info.st_mode))
        self.assertTrue(stat.S_ISREG(info.st_mode))
        self.assertEqual(info.st_size, 11)
        self.assertEqual(info.st_mode & 0o777, 0o777)

        # Make sure we can stat the top-level entities
        for path in ('/', '/user', '/collection'):
            info = sftpClient.stat(path)
            self.assertTrue(stat.S_ISDIR(info.st_mode))
            self.assertFalse(stat.S_ISREG(info.st_mode))
            self.assertEqual(info.st_mode & 0o777, 0o777)

        sftpClient.close()
        client.close()

        # Test that any username other than anonymous will fail using auth_none.
        sock = socket.socket()
        sock.connect(('localhost', TEST_PORT))
        trans = paramiko.Transport(sock)
        trans.connect()
        with self.assertRaises(paramiko.ssh_exception.BadAuthenticationType):
            trans.auth_none('')
        trans.close()
        sock.close()

        sock = socket.socket()
        sock.connect(('localhost', TEST_PORT))
        trans = paramiko.Transport(sock)
        trans.connect()
        with self.assertRaises(paramiko.ssh_exception.BadAuthenticationType):
            trans.auth_none('eponymous')
        trans.close()
        sock.close()

        # Test that a connection can be opened for anonymous access using auth_none.
        sock = socket.socket()
        sock.connect(('localhost', TEST_PORT))
        trans = paramiko.Transport(sock)
        trans.connect()
        trans.auth_none(username='anonymous')
        sftpClient = paramiko.SFTPClient.from_transport(trans)

        # Only public data should be visible
        self.assertEqual(set(sftpClient.listdir('/user')), {'admin', 'regularuser'})
        self.assertEqual(sftpClient.listdir('/collection'), ['public collection'])
        self.assertEqual(sftpClient.listdir('/user/admin'), ['Public'])

        # Make sure the client cannot distinguish between a resource that does not exist
        # vs. one they simply don't have read access to.
        with self.assertRaisesRegex(IOError, 'No such file'):
            sftpClient.listdir('/user/regularuser/Private')

        with self.assertRaisesRegex(IOError, 'No such file'):
            sftpClient.file('/user/regularuser/Private/test.txt/test.txt', 'r')

        sftpClient.close()
        trans.close()
        sock.close()

        # Test anonymous access
        client = paramiko.SSHClient()
        client.load_system_host_keys()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        client.connect(
            'localhost', TEST_PORT, username='anonymous', password='', look_for_keys=False,
            allow_agent=False)
        sftpClient = client.open_sftp()

        # Only public data should be visible
        self.assertEqual(set(sftpClient.listdir('/user')), {'admin', 'regularuser'})
        self.assertEqual(sftpClient.listdir('/collection'), ['public collection'])
        self.assertEqual(sftpClient.listdir('/user/admin'), ['Public'])

        # Make sure the client cannot distinguish between a resource that does not exist
        # vs. one they simply don't have read access to.
        with self.assertRaisesRegex(IOError, 'No such file'):
            sftpClient.listdir('/user/regularuser/Private')

        with self.assertRaisesRegex(IOError, 'No such file'):
            sftpClient.file('/user/regularuser/Private/test.txt/test.txt', 'r')

        sftpClient.close()
        client.close()
