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
import atexit
import os
import pprint
import pymongo
import shutil
import signal
import subprocess
import time

from six.moves import range


Config = [{
    'dir': '/tmp/mongodb1',
    'port': 27070
    }, {
    'dir': '/tmp/mongodb2',
    'port': 27071
    }, {
    'dir': '/tmp/mongodb3',
    'port': 27072
    }]
ReplicaSetName = 'replicaset'


def getMongoClient(uri, init=False, timeout=30):
    """
    Get a mongodb client from a uri or an index into the Config list.  This can
    initiate a replica set if needed.

    :param uri: the mongo uri.  If this is an integer, the uri is constructed
                from the Config list.
    :param init: if set and a client connection is requested, initiate the
                 replica set with this configuration.
    :param timeout: timeout in seconds.
    :returns: the client connection.
    """
    if isinstance(uri, int):
        uri = 'mongodb://localhost:%d/admin' % Config[uri]['port']
    starttime = time.time()
    client = None
    while time.time() < starttime + timeout:
        try:
            client = pymongo.MongoClient(uri)
            if init:
                try:
                    client.admin.command({'replSetInitiate': init})
                    break
                except pymongo.errors.OperationFailure:
                    time.sleep(0.5)
            else:
                break
        except pymongo.errors.ConnectionFailure:
            time.sleep(0.5)
    if not client:
        raise
    return client


def pauseMongoReplicaSet(pauseList, verbose=0):
    """
    Pause or resume our various mongo servers to make the primary shift.

    :param pauseList: a list of servers to change the state of.  A value of
                      True will pause a server.  A value of False will resume
                      it.
    :param verbose: verbosity for logging.
    """
    changed = False
    for idx in range(min(len(pauseList), len(Config))):
        server = Config[idx]
        if ('proc' in server and
                bool(pauseList[idx]) != server.get('paused', False)):
            if pauseList[idx]:
                os.kill(server['proc'].pid, signal.SIGSTOP)
            else:
                os.kill(server['proc'].pid, signal.SIGCONT)
            server['paused'] = pauseList[idx]
            changed = True
    if changed or verbose >= 1:
        status = []
        for server in Config:
            if server.get('paused', False):
                status.append(8)
            else:
                status.append((1, 2))
        client, stat = waitForRSStatus(getMongoClient(min([
            idx for idx in range(len(Config))
            if not Config[idx].get('paused', False)])), status=status,
            verbose=verbose)
        if verbose >= 2:
            pprint.pprint(stat)


def startMongoReplicaSet(timeout=60, verbose=0):
    """
    Start three mongo servers on ports 27070, 27071, 27072.  Configure a
    replica set between the three of them.  Makre sure they shut down when the
    current process ends.

    :param timeout: maximum time to wait for a mongo server to be ready.
    :param verbose: verbosity for logging.
    """
    atexit.register(stopMongoReplicaSet, False)
    if verbose >= 1:
        print('Preparing mongo replica set')
    # Create a set of directories in /tmp and start mongod processes
    kwargs = {}
    if verbose < 3:
        devnull = open(os.devnull, 'wb')
        kwargs = {'stdout': devnull, 'stderr': subprocess.STDOUT}
    for server in Config:
        if os.path.exists(server['dir']):
            shutil.rmtree(server['dir'])
        os.makedirs(server['dir'])

        proc = subprocess.Popen([
            os.environ.get('MONGOD_EXECUTABLE', 'mongod'),
            '--dbpath', server['dir'],
            '--port', str(server['port']),
            '--replSet', ReplicaSetName,
            '--noprealloc', '--smallfiles', '--oplogSize', '128'], **kwargs)
        server['proc'] = proc

    replConf = {
        '_id': ReplicaSetName, 'version': 1,
        'members': [{'_id': i, 'host': '127.0.0.1:%d' % Config[i]['port']}
                    for i in range(len(Config))]}
    client, stat = waitForRSStatus(getMongoClient(0, replConf, timeout),
                                   [(1, 2), (2, 1), (2, 1)], timeout,
                                   verbose=verbose)
    # Reorder our config records so that the primary set is first
    if Config[0]['lastState'] != 1:
        for idx in range(1, len(Config)):
            if Config[idx]['lastState'] == 1:
                Config[0], Config[idx] = Config[idx], Config[0]
                break
    if verbose >= 1:
        print('Mongo replica set ready')
        conf = client.local.system.replset.find_one()
        pprint.pprint(conf)
    if verbose >= 2:
        pprint.pprint(stat)


def stepDownMongoReplicaSet(uri):
    """
    Ask one of the servers to step down from being primary.

    :param uri: the mongo uri.  If this is an integer, the uri is constructed
                from the Config list.
    """
    client = getMongoClient(uri)
    numtries = 3
    for trynum in range(numtries):
        try:
            client.admin.command({'replSetStepDown': 60})
            break
        except pymongo.errors.AutoReconnect:
            # we expect the connection to close, so this is not an error
            break
        except pymongo.errors.OperationFailure:
            if trynum + 1 == numtries:
                raise
            time.sleep(5)


def stopMongoReplicaSet(graceful=True, purgeFiles=True):
    """
    Try to stop all of the mongo servers.

    :param graceful: if True, try to let the servers stop gracefully.
                     Otherwise, kill them quickly.
    :param purgeFiles: if True, then after stopping the server, delete the
                       files it was using.
    """
    if graceful:
        pauseList = [False for server in Config]
        pauseMongoReplicaSet(pauseList)
    for server in Config:
        if 'proc' in server:
            if graceful:
                server['proc'].terminate()
                server['proc'].wait()
                del server['proc']
            else:
                try:
                    server['proc'].kill()
                    del server['proc']
                except Exception:
                    # If this fails, we have lost our power to affect the
                    # process, so it does no good to complain about it.
                    print("Can't kill a mongod replica set server")
            if purgeFiles:
                if os.path.exists(server['dir']):
                    shutil.rmtree(server['dir'])


def getOrderedRSStatus(client, minMembers):
    """
    Get the status of the mongodb replica set and order the members to match
    the Config list.

    :param client: an existing client connection to a mongodb.
    :param minMembers: the number of members to ensure exist and are in the
                       desired order.
    :returns: current status of the replica set with the members in the order
              of the Config list, or None.
    """
    if minMembers > len(Config):
        return None
    try:
        stat = client.admin.command('replSetGetStatus')
        if 'members' not in stat or len(stat['members']) < minMembers:
            return None
        members = []
        for idx in range(minMembers):
            member = None
            for entry in stat['members']:
                if (entry['name'].split(':')[-1] ==
                        str(Config[idx]['port'])):
                    member = entry
            if not member:
                return None
            members.append(member)
        stat['members'] = members
        return stat
    except (pymongo.errors.OperationFailure, pymongo.errors.AutoReconnect):
        return None


def waitForRSStatus(client, status=[1], timeout=60, verbose=0):
    """
    Wait until a mongodb client has a replica set status record that matches a
    specific state.

    :param client: an existing client connection to a mongodb.
    :param status: a list of statuses required for success.  The first
                   len(status) members must match the values of the list.  The
                   entries in the list can be tuples, in which case the member
                   state can be any value within that tuple.
    :param timeout: timeout in seconds.
    :param verbose: verbosity for logging.
    :returns: the client connection.
    :returns: current status of the replica set.
    """
    stat = None
    starttime = time.time()
    okay = False
    while time.time() < starttime + timeout:
        stat = getOrderedRSStatus(client, len(status))
        if stat:
            okay = True
            numberOfPrimary = 0
            numberOfSecondary = 0
            for idx in range(len(status)):
                member = stat['members'][idx]
                numberOfPrimary += (member['state'] == 1)
                numberOfSecondary += (member['state'] == 2)
                if isinstance(status[idx], (list, tuple)):
                    if member['state'] not in status[idx]:
                        okay = False
                elif member['state'] != status[idx]:
                    okay = False
                Config[idx]['lastState'] = member['state']
            if ((numberOfPrimary != 1 and numberOfSecondary > 0) or
                    numberOfPrimary > 1):
                okay = False
            if verbose >= 2:
                print([memb['state'] for memb in stat['members']],
                      status, numberOfPrimary, numberOfSecondary)
            if okay:
                break
        time.sleep(0.5)
    if not stat or not okay:
        raise Exception('Status does not match')
    return client, stat


if __name__ == '__main__':
    """
    Provide a simple stand-alone program so that developers can run a more
    persistent replica set for longer term testing.
    a modified conf file to simulate an S3 store.
    """
    parser = argparse.ArgumentParser(
        description='Run a mongo replica set on ports 27070, 27071, 27072 '
        'with a replica set named "%s".  All data will be lost when they are '
        'stopped.' % ReplicaSetName)
    parser.add_argument('-v', '--verbose', action='count',
                        help='Increase verbosity.', default=0)
    parser.add_argument('--pause', action='count',
                        help='Pause and unpause servers.', default=0)
    args = parser.parse_args()
    startMongoReplicaSet(verbose=args.verbose)
    if args.pause:
        time.sleep(20)
        print('Pausing first server')
        pauseMongoReplicaSet([True], verbose=args.verbose)
        time.sleep(20)
        print('Unpausing first server; pausing second server')
        pauseMongoReplicaSet([False, True], verbose=args.verbose)
        time.sleep(20)
        print('Unpausing all servers')
        pauseMongoReplicaSet([False, False], verbose=args.verbose)
        time.sleep(20)
        print('Checking server status')
        pauseMongoReplicaSet([], verbose=args.verbose)
    while True:
        try:
            time.sleep(10000)
        except KeyboardInterrupt:
            break
    stopMongoReplicaSet()
