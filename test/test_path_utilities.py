import pytest

from girder.utility import path


@pytest.mark.parametrize('raw,encoded', [
    ('abcd', 'abcd'),
    ('/', '\\-'),
    ('\\', '\\\\'),
    ('/\\', '\\-\\\\'),
    ('\\//\\', '\\\\\\-\\-\\\\'),
    ('a\\\\b//c\\d', 'a\\\\\\\\b\\-\\-c\\\\d')
])
def testCodec(raw, encoded):
    assert path.encode(raw) == encoded
    assert path.decode(encoded) == raw


@pytest.mark.parametrize('pth,tokens', [
    ('abcd', ['abcd']),
    ('/abcd', ['', 'abcd']),
    ('/ab/cd/ef/gh', ['', 'ab', 'cd', 'ef', 'gh']),
    ('/ab/cd//', ['', 'ab', 'cd', '', '']),
    ('ab\\-cd', ['ab/cd']),
    ('ab\\-c/d', ['ab/c', 'd']),
    ('ab\\-/cd', ['ab/', 'cd']),
    ('ab/\\-cd', ['ab', '/cd']),
    ('ab\\\\/cd', ['ab\\', 'cd']),
    ('ab\\\\/\\\\cd', ['ab\\', '\\cd']),
    ('ab\\\\\\-\\\\cd', ['ab\\/\\cd']),
    ('/\\\\abcd\\\\/', ['', '\\abcd\\', '']),
    ('/\\\\\\\\/\\-/\\\\', ['', '\\\\', '/', '\\'])
])
def testSplitAndJoin(pth, tokens):
    assert path.split(pth) == tokens
    assert path.join(tokens) == pth
