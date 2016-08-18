#!/usr/bin/env python
# -*- coding: utf-8 -*-

###############################################################################
#  Copyright 2013 Kitware Inc.
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

import asyncore
import email
import os
import smtpd
import sys
import threading
import time

from six.moves import queue, range

_startPort = 31000
_maxTries = 100


class MockSmtpServer(smtpd.SMTPServer):
    mailQueue = queue.Queue()

    def __init__(self, localaddr, remoteaddr, decode_data=False):
        kwargs = {}
        if sys.version_info >= (3, 5):
            # Python 3.5+ prints a warning if 'decode_data' isn't explicitly
            # specified, but earlier versions don't accept the argument at all
            kwargs['decode_data'] = decode_data
        # smtpd.SMTPServer is an old-style class in Python2,
        # so super() can't be used
        smtpd.SMTPServer.__init__(self, localaddr, remoteaddr, **kwargs)

    def process_message(self, peer, mailfrom, rcpttos, data):
        self.mailQueue.put(data)


class MockSmtpReceiver(object):
    def __init__(self):
        self.address = None
        self.smtp = None
        self.thread = None

    def start(self):
        """
        Start the mock SMTP server. Attempt to bind to any port within the
        range specified by _startPort and _maxTries.  Bias it with the pid of
        the current process so as to reduce potential conflicts with parallel
        tests that are started nearly simultaneously.
        """
        for porttry in range(_maxTries):
            port = _startPort + ((porttry + os.getpid()) % _maxTries)
            try:
                self.address = ('localhost', port)
                self.smtp = MockSmtpServer(self.address, None)
                break
            except Exception:
                pass
        else:
            raise Exception('Could not bind to any port for Mock SMTP server')

        self.thread = threading.Thread(target=self.loop)
        self.thread.daemon = True
        self.thread.start()

    def loop(self):
        """
        Instead of calling asyncore.loop directly, wrap it with a small
        timeout.  This prevents using 100% cpu and still allows a graceful
        exit.
        """
        while len(asyncore.socket_map):
            asyncore.loop(timeout=0.5, use_poll=True)

    def stop(self):
        """Stop the mock STMP server"""
        self.smtp.close()
        self.thread.join()

    def getMail(self, parse=False):
        """
        Return the message at the front of the queue.
        Raises Queue.Empty exception if there are no messages.

        :param parse: Whether to parse the email into an email.message.Message
            object. If False, just returns the raw email string.
        :type parse: bool
        """
        msg = self.smtp.mailQueue.get(block=False)

        if parse:
            return email.message_from_string(msg)
        else:
            return msg

    def isMailQueueEmpty(self):
        """Return whether or not the mail queue is empty"""
        return self.smtp.mailQueue.empty()

    def waitForMail(self, timeout=10):
        """
        Waits for mail to appear on the queue. Returns "True" as soon as the
        queue is not empty, or "False" if the timeout was reached before any
        mail appears.

        :param timeout: Timeout in seconds.
        :type timeout: float
        """
        startTime = time.time()
        while True:
            if not self.isMailQueueEmpty():
                return True
            if time.time() > startTime + timeout:
                return False
            time.sleep(0.1)
