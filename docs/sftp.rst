SFTP Service
============

In addition to its normal HTTP server, the Girder package also includes a lightweight SFTP
server that can be used to serve the same underlying data using the
`SSH File Transfer Protocol <https://en.wikipedia.org/wiki/SSH_File_Transfer_Protocol>`_. This
server provides a read-only view of the data in a Girder instance, and supports either anonymous
access (users must pass the username "anonymous" in their SFTP client), or authenticated access
with their Girder login name and password. This protocol can make it much easier to download large
nested datasets with many individual files, and is tolerant to network failure since it supports
resuming interrupted downloads of entire data hierarchies.

After installing the Girder package via pip, you should now see the ``girder`` executable
in your PATH. Running ``girder sftpd`` will start the SFTP server using the same database configuration
as the main Girder HTTP server.

The SFTP server requires a private key file for secure communication with clients. If you do
not pass an explicit path to an RSA private key file, the service will look for one at
``~/.ssh/id_rsa``. It's recommended to make a special key just for the SFTP service, e.g.::

    ssh-keygen -t rsa -b 2048 -f my_key.rsa -N ''
    girder sftpd -i my_key.rsa

You can control the port on which the server binds by passing a ``-p <port>`` argument to the
server CLI. The default port is 8022.

.. note:: If SFTP clients are logging in as a user with two-factor authentication (one-time passwords) enabled, they
   must append the one-time authentication code to the user's basic password.
