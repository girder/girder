import datetime
from girder.exceptions import ValidationException
from girder.models.model_base import Model
from girder.models.token import Token, genToken
from girder.models.user import User

class Code(Model):
    def initialize(self):
        self.name = 'oauth_code'
        self.ensureIndex(('expires', {'expireAfterSeconds': 0}))
        self.ensureIndex('code')

    def validate(self, doc):
        return doc

    def createCode(self, client, scope, user, days=7):
        now = datetime.datetime.utcnow()

        return self.save({
            'clientId': client['_id'],
            'code': genToken(length=32),
            'created': now,
            'expires': now + datetime.timedelta(days=float(days)),
            'scope': scope,
            'userId': user['_id'],
        })

    def createToken(self, code):
        doc = self.findOne({'code': code})
        if doc is None:
            raise ValidationException('Invalid access code.')

        user = User().load(doc['userId'], force=True, exc=True)
        token = Token().createToken(user, scope=doc['scope'].split())
        token['oauthClientId'] = doc['clientId']
        return Token().save(token)
