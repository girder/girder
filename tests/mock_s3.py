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

import argparse
import cherrypy
import logging
import threading

import moto.server

_defaultPort = 50003


def startMockS3Server(makeBuckets=True):
    """
    Start a server using the defaults and adding a configuration parameter to
    the system so that the s3 assetstore handler will know to use this
    server.
    """
    # turn off logging from the S3 server
    logging.getLogger('werkzeug').setLevel(logging.CRITICAL)
    cherrypy.config['server'].update({
        's3server': 'http://127.0.0.1:%d' % _defaultPort,
        's3server_make_buckets': makeBuckets,
        })
    server = MockS3Server()
    server.start()


class MockS3Server(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.daemon = True

    def run(self):
        """Start and run the mock S3 server."""
        app = moto.server.DomainDispatcherApplication(_create_app,
                                                      service='s3bucket_path')
        moto.server.run_simple('0.0.0.0', _defaultPort, app, threaded=True)


def _create_app(service):
    """
    Create the S3 server using moto, altering the responses to allow CORS
    requests.
    :param service: the amazon service we wish to mimic.  This should probably
                    be 's3bucket_path'.
    """
    app = moto.server.create_backend_app(service)

    @app.after_request
    def after_request(response):
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Methods',
                             'HEAD, GET, PUT, POST, OPTIONS, DELETE')
        response.headers.add(
            'Access-Control-Allow-Headers',
            'Content-Disposition,Content-Type,'
            'x-amz-meta-authorized-length,x-amz-acl,x-amz-meta-uploader-ip,'
            'x-amz-meta-uploader-id'
            )
        response.headers.add('Access-Control-Expose-Headers', 'ETag')
        return response

    return app


if __name__ == '__main__':
    """
    Provide a simple stand-alone program so that developers can run girder with
    a modified conf file to simulate an S3 store.
    """
    parser = argparse.ArgumentParser(
        description='Run a mock S3 server.  All data will be lost when then '
        'is stopped.')
    parser.add_argument('-p', '--port', type=int, help='The port to run on',
                        default=_defaultPort)
    args = parser.parse_args()
    app = moto.server.DomainDispatcherApplication(_create_app,
                                                  service='s3bucket_path')
    moto.server.run_simple('0.0.0.0', args.port, app, threaded=True)
