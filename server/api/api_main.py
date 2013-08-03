from v1 import user as user1,\
               api_docs as api_docs1

class ApiDocs():
    exposed = True

    def GET(self):
        # TODO
        return "should display links to available api versions"

def addApiToNode(node):
    node.api = ApiDocs()
    node.api = _addV1ToNode(node.api)

    return node

def _addV1ToNode(node):
    node.v1 = api_docs1.ApiDocs()
    node.v1.user = user1.User()
    # etc

    return node
