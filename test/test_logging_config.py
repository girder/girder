import os
import pytest
import shutil
import sys
import tempfile

import girder
from girder import logger, logprint, logStdoutStderr
from girder.utility import config

INFO_MSG = 'Log info message'
ERROR_MSG = 'Log error message'


@pytest.fixture
def tempLog():
    logRoot = tempfile.mkdtemp()
    infoFile = os.path.join(logRoot, 'config_info.log')
    errorFile = os.path.join(logRoot, 'config_error.log')
    cfg = config.getConfig()
    old, cfg['logging'] = cfg['logging'], {
        'log_root': logRoot,
        'info_log_file': infoFile,
        'error_log_file': errorFile,
        'original_error_log_file': errorFile
    }

    yield cfg['logging']

    cfg['logging'] = old
    shutil.rmtree(logRoot)


def configureLogging(logConfig=None, oneFile=False):
    cfg = config.getConfig()
    if oneFile:
        cfg['logging']['error_log_file'] = cfg['logging']['info_log_file']
    else:
        cfg['logging']['error_log_file'] = cfg['logging']['original_error_log_file']
    if os.path.exists(cfg['logging']['info_log_file']):
        os.unlink(cfg['logging']['info_log_file'])
    if os.path.exists(cfg['logging']['error_log_file']):
        os.unlink(cfg['logging']['error_log_file'])
    cfg['logging'].update(logConfig or {})

    girder._attachFileLogHandlers()

    return cfg['logging']


def testFileRotation(tempLog):
    tempLog = configureLogging({
        'log_access': ['screen', 'info'],
        'log_quiet': True,
        'log_max_size': '1 kb',
        'log_backup_count': 2,
        'log_level': 'DEBUG',
    })

    logger.info(INFO_MSG)
    logger.error(ERROR_MSG)
    infoSize = os.path.getsize(tempLog['info_log_file'])
    errorSize = os.path.getsize(tempLog['error_log_file'])
    assert os.path.exists(tempLog['info_log_file'] + '.1') is False
    assert os.path.exists(tempLog['error_log_file'] + '.1') is False
    logger.info(INFO_MSG)
    logger.error(ERROR_MSG)
    newInfoSize = os.path.getsize(tempLog['info_log_file'])
    newErrorSize = os.path.getsize(tempLog['error_log_file'])
    deltaInfo = newInfoSize - infoSize
    deltaError = newErrorSize - errorSize
    assert deltaInfo > len(INFO_MSG)
    assert deltaError > len(ERROR_MSG)
    while newInfoSize < 1024 * 1.5:
        logger.info(INFO_MSG)
        newInfoSize += deltaInfo
    while newErrorSize < 1024 * 1.5:
        logger.error(ERROR_MSG)
        newErrorSize += deltaError
    assert os.path.exists(tempLog['info_log_file'] + '.1') is True
    assert os.path.exists(tempLog['error_log_file'] + '.1') is True
    assert os.path.exists(tempLog['info_log_file'] + '.2') is False
    assert os.path.exists(tempLog['error_log_file'] + '.2') is False
    while newInfoSize < 1024 * 3.5:
        logger.info(INFO_MSG)
        newInfoSize += deltaInfo
    while newErrorSize < 1024 * 3.5:
        logger.error(ERROR_MSG)
        newErrorSize += deltaError
    assert os.path.exists(tempLog['info_log_file'] + '.1') is True
    assert os.path.exists(tempLog['error_log_file'] + '.1') is True
    assert os.path.exists(tempLog['info_log_file'] + '.2') is True
    assert os.path.exists(tempLog['error_log_file'] + '.2') is True
    assert os.path.exists(tempLog['info_log_file'] + '.3') is False
    assert os.path.exists(tempLog['error_log_file'] + '.3') is False


def testCaptureStdoutAndStderr(tempLog):
    tempLog = configureLogging()
    logStdoutStderr(force=True)

    infoSize1 = os.path.getsize(tempLog['info_log_file'])
    errorSize1 = os.path.getsize(tempLog['error_log_file'])
    print(INFO_MSG)
    infoSize2 = os.path.getsize(tempLog['info_log_file'])
    errorSize2 = os.path.getsize(tempLog['error_log_file'])
    assert infoSize2 > infoSize1
    assert errorSize2 == errorSize1
    print(ERROR_MSG, file=sys.stderr)
    infoSize3 = os.path.getsize(tempLog['info_log_file'])
    errorSize3 = os.path.getsize(tempLog['error_log_file'])
    assert infoSize3 == infoSize2
    assert errorSize3 > errorSize2


def testOneFile(tempLog):
    tempLog = configureLogging({'log_max_info_level': 'CRITICAL'}, oneFile=True)

    logger.info(INFO_MSG)
    infoSize = os.path.getsize(tempLog['info_log_file'])
    errorSize = os.path.getsize(tempLog['error_log_file'])
    assert infoSize == errorSize
    logger.error(ERROR_MSG)
    newInfoSize = os.path.getsize(tempLog['info_log_file'])
    newErrorSize = os.path.getsize(tempLog['error_log_file'])
    assert newInfoSize == newErrorSize
    assert newInfoSize > infoSize


def testInfoMaxLevel(tempLog):
    tempLog = configureLogging({'log_max_info_level': 'CRITICAL'})

    infoSize1 = os.path.getsize(tempLog['info_log_file'])
    errorSize1 = os.path.getsize(tempLog['error_log_file'])
    logger.info(INFO_MSG)
    infoSize2 = os.path.getsize(tempLog['info_log_file'])
    errorSize2 = os.path.getsize(tempLog['error_log_file'])
    assert infoSize2 > infoSize1
    assert errorSize2 == errorSize1
    logger.error(ERROR_MSG)
    infoSize3 = os.path.getsize(tempLog['info_log_file'])
    errorSize3 = os.path.getsize(tempLog['error_log_file'])
    assert infoSize3 > infoSize2
    assert errorSize3 > errorSize2


def testLogPrint(tempLog):
    tempLog = configureLogging({'log_max_info_level': 'INFO'})

    infoSize1 = os.path.getsize(tempLog['info_log_file'])
    errorSize1 = os.path.getsize(tempLog['error_log_file'])
    logprint.info(INFO_MSG)
    infoSize2 = os.path.getsize(tempLog['info_log_file'])
    errorSize2 = os.path.getsize(tempLog['error_log_file'])
    assert infoSize2 > infoSize1
    assert errorSize2 == errorSize1
    logprint.error(ERROR_MSG)
    infoSize3 = os.path.getsize(tempLog['info_log_file'])
    errorSize3 = os.path.getsize(tempLog['error_log_file'])
    # logprint sends to stdout, which we capture except when sent via
    # logprint, so we shouldn't see any additional data on the info log.
    assert infoSize3 == infoSize2
    assert errorSize3 > errorSize2
