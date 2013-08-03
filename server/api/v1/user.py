from ..rest import Resource

class User(Resource):

    @Resource.endpoint
    def GET(self, id=None):
        #TODO
        return {'id': id}
