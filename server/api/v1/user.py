from ..rest import Resource
from models import user as userModel

class User(Resource):

    def __init__(self):
        self.model = userModel.User()

    @Resource.endpoint
    def GET(self, id=None):
        #TODO
        return {'id': id}

    @Resource.endpoint
    def POST(self, **params):
        #TODO
        pass
