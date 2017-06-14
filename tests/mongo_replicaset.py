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
import six
import subprocess
import time

from six.moves import range


def getMongoClient(config, uri=None, init=False, timeout=30):
    """
    Get a mongodb client from a uri or an index into the Config list.  This can
    initiate a replica set if needed.

    :param config: list of servers.
    :param uri: the mongo uri.  If this is an integer, the uri is constructed
                from the config list.  If None, use the route entry in config
                if it exists, or the 0th entry if it does not.
    :param init: if set and a client connection is requested, initiate the
                 replica set with this configuration.
    :param timeout: timeout in seconds.
    :returns: the client connection.
    """
    if uri is None:
        for server in config:
            if server.get('route'):
                uri = 'mongodb://127.0.0.1:%d/admin' % server['port']
        if uri is None:
            uri = 0
    if isinstance(uri, int):
        uri = 'mongodb://localhost:%d/admin' % config[uri]['port']
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


def getOrderedRSStatus(config, client, minMembers, baseIdx):
    """
    Get the status of the mongodb replica set and order the members to match
    the config list.

    :param config: list of servers.
    :param client: an existing client connection to a mongodb.
    :param minMembers: the number of members to ensure exist and are in the
                       desired order.
    :param baseIdx: base entry in the config list.
    :returns: current status of the replica set with the members in the order
              of the config list, or None.
    """
    if minMembers > len(config):
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
                        str(config[baseIdx + idx]['port'])):
                    member = entry
            if not member:
                return None
            members.append(member)
        stat['members'] = members
        return stat
    except (pymongo.errors.OperationFailure, pymongo.errors.AutoReconnect):
        return None


def makeConfig(port=27070, replicaset='replicaset', servers=3, shard=False,
               sharddb='gridfs', shardcollection='chunk', shardkey='uuid',
               dirroot='/tmp/girderdb', **kwargs):
    """
    Make a config array.

    :param port: the starting port number.
    :param replicaset: name for the replicaset.
    :param servers: number of servers to start.  For shards, this is the number
        of shards; there will also be a config server and a routing server.
    :param shard: True to make a shard configuration, false for a replica set.
    :param sharddb: if sharding is used, the name of a database to shard.
    :param shardcollection: if sharding is used, the name of a collection to
        shard.
    :param shardkey: if sharding is used, the key to shard on in a collection.
    :param dirroot: base temp directory name.
    :returns: a new configuration array.
    """
    try:
        cmd = [os.environ.get('MONGOD_EXECUTABLE', 'mongod'), '--version']
        version = subprocess.Popen(cmd, stdout=subprocess.PIPE).stdout.read()
        version = tuple(int(part) for part in version.split(
            'db version v')[1].split()[0].strip().split('.'))
    except Exception:
        version = (0, 0, 0)
    config = []
    if shard:
        config.append({
            'dir': '%scfg' % dirroot,
            'config': True,
            'port': port + 1,
            'replicaset': replicaset
        })
        if version < (3, 2):
            del config[-1]['replicaset']
        for i in range(servers):
            config.append({
                'dir': '%s%d' % (dirroot, i + 1),
                'port': port + 2 + i,
                'shard': True
            })
        # On a mongo 3 server, this has to be started last, so add it at the
        # end of the list
        config.append({
            'route': True,
            'port': port,
            'db': sharddb,
            'collection': shardcollection,
            'shardkey': shardkey,
        })
    else:
        for i in range(servers):
            config.append({
                'dir': '%s%d' % (dirroot, i + 1),
                'port': port + i,
                'replicaset': replicaset
            })
    return config


def pauseMongoReplicaSet(config, pauseList, verbose=0):
    """
    Pause or resume our various mongo servers to make the primary shift.

    :param config: list of servers.
    :param pauseList: a list of servers to change the state of.  A value of
                      True will pause a server.  A value of False will resume
                      it.
    :param verbose: verbosity for logging.
    """
    changed = False
    for idx in range(min(len(pauseList), len(config))):
        server = config[idx]
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
        for server in config:
            if server.get('paused', False):
                status.append(8)
            else:
                status.append((1, 2))
        client, stat = waitForRSStatus(config, getMongoClient(config, min([
            idx for idx in range(len(config))
            if not config[idx].get('paused', False)])), status=status,
            verbose=verbose)
        if verbose >= 2:
            pprint.pprint(stat)


def _startMongoProcesses(config, timeout=60, verbose=0):
    """
    Create a set of directories in /tmp and start mongod and mongos processes.

    :param config: list of servers.
    :param timeout: maximum time to wait for a mongo server to be ready.
    :param verbose: verbosity for logging.
    :returns: replicasets: an object with a key for each created replicaset.
        Each has a value which is the offset within the config list of the
        first server in the replica set.
    :returns: shardRoute: None if this is not a sharded set.  Otherwise, the
        server entry for the shard route.
    """
    kwargs = {}
    if verbose < 3:
        devnull = open(os.devnull, 'wb')
        kwargs = {'stdout': devnull, 'stderr': subprocess.STDOUT}
    replicasets = {}
    shardRoute = None
    for idx, server in enumerate(config):
        if not server.get('route'):
            cmd = [
                os.environ.get('MONGOD_EXECUTABLE', 'mongod'),
                '--noprealloc', '--smallfiles', '--oplogSize', '128'
            ]
        else:
            shardRoute = server
            cfgsvr = six.next(entry for i, entry in enumerate(config) if entry.get('config'))
            cmd = [os.environ.get('MONGOS_EXECUTABLE', 'mongos'),
                   '--configdb', '%s127.0.0.1:%d' % (
                   cfgsvr['replicaset'] + '/' if 'replicaset' in cfgsvr else '',
                   cfgsvr['port'])]
        cmd.extend(['--port', str(server['port'])])
        if server.get('dir'):
            if os.path.exists(server['dir']):
                shutil.rmtree(server['dir'])
            os.makedirs(server['dir'])
            cmd.extend(['--dbpath', server['dir']])
        if 'replicaset' in server:
            cmd.extend(['--replSet', server['replicaset']])
            if not server['replicaset'] in replicasets:
                replicasets[server['replicaset']] = idx
        if server.get('config'):
            cmd.append('--configsvr')
        if server.get('shard'):
            cmd.append('--shardsvr')
        if verbose >= 1:
            print(' '.join(cmd))
        proc = subprocess.Popen(cmd, **kwargs)
        server['proc'] = proc
        # Make sure we can query the database before moving on to starting the
        # next one.
        if not server.get('route'):
            _waitForStatus('127.0.0.1:%d' % server['port'], timeout)
    return replicasets, shardRoute


def startMongoReplicaSet(config, timeout=60, verbose=0):
    """
    Start mongo servers.  These can be part of replica sets, config servers,
    or shard servers.  Configure the replica sets and the shards.  Make sure
    they shut down when the current process ends.

    :param config: list of servers.
    :param timeout: maximum time to wait for a mongo server to be ready.
    :param verbose: verbosity for logging.
    """
    atexit.register(stopMongoReplicaSet, config, False)
    replicasets, shardRoute = _startMongoProcesses(config, timeout, verbose)
    for replicaset in replicasets:
        replConf = {
            '_id': replicaset, 'version': 1,
            'members': [{'_id': i, 'host': '127.0.0.1:%d' % server['port']}
                        for i, server in enumerate(config)
                        if server.get('replicaset') == replicaset]
        }
        client, stat = waitForRSStatus(
            config, getMongoClient(
                config, replConf['members'][0]['_id'], replConf, timeout),
            [(1, 2)] + [(2, 1)] * (len(replConf['members']) - 1),
            timeout, verbose=verbose, baseIdx=replicasets[replicaset])
        if verbose >= 2:
            print('Mongo replica set ready')
            conf = client.local.system.replset.find_one()
            pprint.pprint(conf)
    if not shardRoute:  # just a replicaset
        # Reorder our config records so that the primary set is first
        if config[0]['lastState'] != 1:
            for idx in range(1, len(config)):
                if config[idx]['lastState'] == 1:
                    config[0], config[idx] = config[idx], config[0]
                    break
        if verbose >= 1:
            print('Mongo replica set ready')
            conf = client.local.system.replset.find_one()
            pprint.pprint(conf)
    else:  # sharding
        client = getMongoClient(config, timeout=timeout)
        for server in config:
            if server.get('shard'):
                client.admin.command('addShard', '127.0.0.1:%d' % server['port'])
        if shardRoute.get('db'):
            client.admin.command('enableSharding', shardRoute['db'])
            if shardRoute.get('collection') and shardRoute.get('shardkey'):
                client.admin.command(
                    'shardCollection',
                    '%s.%s' % (shardRoute['db'], shardRoute['collection']),
                    key={shardRoute['shardkey']: 1})
        stat = client.admin.command('serverStatus')
        if verbose >= 1:
            print('Mongo sharding server ready')
    if verbose >= 2:
        pprint.pprint(stat)


def stepDownMongoReplicaSet(config, uri):
    """
    Ask one of the servers to step down from being primary.

    :param config: list of servers.
    :param uri: the mongo uri.  If this is an integer, the uri is constructed
                from the config list.
    """
    client = getMongoClient(config, uri)
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


def stopMongoReplicaSet(config, graceful=True, purgeFiles=True):
    """
    Try to stop all of the mongo servers.

    :param config: list of servers.
    :param graceful: if True, try to let the servers stop gracefully.
                     Otherwise, kill them quickly.
    :param purgeFiles: if True, then after stopping the server, delete the
                       files it was using.
    """
    if graceful:
        pauseList = [False for server in config]
        pauseMongoReplicaSet(config, pauseList)
    for server in config:
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
                if 'dir' in server and os.path.exists(server['dir']):
                    shutil.rmtree(server['dir'])


def waitForRSStatus(config, client, status=[1], timeout=60, verbose=0,
                    baseIdx=0):
    """
    Wait until a mongodb client has a replica set status record that matches a
    specific state.

    :param config: list of servers.
    :param client: an existing client connection to a mongodb.
    :param status: a list of statuses required for success.  The first
                   len(status) members must match the values of the list.  The
                   entries in the list can be tuples, in which case the member
                   state can be any value within that tuple.
    :param timeout: timeout in seconds.
    :param verbose: verbosity for logging.
    :param baseIdx: base entry in the config list.
    :returns: the client connection.
    :returns: current status of the replica set.
    """
    stat = None
    starttime = time.time()
    okay = False
    while time.time() < starttime + timeout:
        stat = getOrderedRSStatus(config, client, len(status), baseIdx)
        if verbose >= 3:
            print('Status: %r, waiting for %r' % (stat, status))
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
                config[baseIdx + idx]['lastState'] = member['state']
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


def _waitForStatus(uri, timeout):
    """
    Check if we can get status from a database server.  Raise an exception if
    not.

    :param uri: connection uri.
    :param timeout: maximum time to wait for a mongo server to be ready.
    :returns: status.
    """
    starttime = time.time()
    while time.time() - starttime < timeout:
        try:
            client = pymongo.MongoClient(uri)
            stat = client.admin.command('serverStatus')
            return stat
        except Exception:
            time.sleep(0.1)
    raise


if __name__ == '__main__':
    """
    Provide a simple stand-alone program so that developers can run a more
    persistent replica set for longer term testing.
    a modified conf file to simulate an S3 store.
    """
    parser = argparse.ArgumentParser(
        description='Run a mongo replica set on sequential ports or run '
        'a mongo sharded database with one sharding server, one config '
        'server, and multiple shards on sequential ports.  All data will be '
        'discarded when mongo is stopped.')
    parser.add_argument(
        '--dirroot', default='/tmp/mongodb',
        help='The root name of directories to create.  Multiple directories '
        'e created with paths like <dirroot>1, <dirroot>2.  They are deleted '
        'en the program finishes.  Default /tmp/mongodb.')
    parser.add_argument(
        '--pause', action='count',
        help='Pause and unpause replicateset servers.', default=0)
    parser.add_argument(
        '--port', default=27070, type=int,
        help='Starting port number.  Default 27070')
    parser.add_argument(
        '--replicaset', default='replicaset',
        help='Replica set name (on shards, this is the configuration replica '
        'set name).  Default replicaset.')
    parser.add_argument(
        '--servers', default=3, type=int, help='Number of servers.  For '
        'sharding, this is the number of shards; there is also a config '
        'server and a shard router.  Default 3.')
    parser.add_argument(
        '--shard', action='store_true', help='Create a sharding server.')
    parser.add_argument(
        '--sharddb', default='gridfs',
        help='Name of a database to set as sharded.  Default gridfs.')
    parser.add_argument(
        '--shardcollection', default='chunk',
        help='Name of a collection to set as sharded.  Default chunk.')
    parser.add_argument(
        '--shardkey', default='uuid',
        help='Name of an index to use for sharding.  Default uuid.')
    parser.add_argument(
        '-v', '--verbose', action='count', help='Increase verbosity.',
        default=0)
    args = parser.parse_args()
    config = makeConfig(**vars(args))
    startMongoReplicaSet(config=config, verbose=args.verbose)
    if args.pause and not args.shard:
        time.sleep(20)
        print('Pausing first server')
        pauseMongoReplicaSet(config, [True], verbose=args.verbose)
        time.sleep(20)
        print('Unpausing first server; pausing second server')
        pauseMongoReplicaSet(config, [False, True], verbose=args.verbose)
        time.sleep(20)
        print('Unpausing all servers')
        pauseMongoReplicaSet(config, [False, False], verbose=args.verbose)
        time.sleep(20)
        print('Checking server status')
        pauseMongoReplicaSet(config, [], verbose=args.verbose)
    while True:
        try:
            time.sleep(10000)
        except KeyboardInterrupt:
            break
    stopMongoReplicaSet(config=config)
