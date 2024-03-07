from pytest_girder.assertions import assertStatusOk
from pytest_girder.utils import getResponseBody


def testApiDocsContent(server):
    """
    Test content of API documentation page.
    """
    resp = server.request(path='/api/v1', method='GET', isJson=False, prefix='')
    assertStatusOk(resp)
    body = getResponseBody(resp)

    assert 'Girder - REST API Documentation' in body
    assert 'id="swagger-ui-container"' in body
