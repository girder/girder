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

    def createCode(self, client, scope, user, days=1):
        now = datetime.datetime.utcnow()

        return self.save({
            'clientId': client['_id'],
            'code': genToken(length=32),
            'created': now,
            'expires': now + datetime.timedelta(days=float(days)),
            'scope': scope,
            'userId': user['_id'],
        })

    def createToken(self, code, client, redirect, secret):
        doc = self.findOne({'code': code})
        if doc is None:
            raise ValidationException('Invalid access code.')

        if doc['clientId'] != client['_id']:
            raise ValidationException('OAuth client ID does not match.')

        if secret != client['secret']:
            raise ValidationException('OAuth client secret is incorrect.')

        if redirect not in client['authorizedRedirects']:
            raise ValidationException('Invalid redirect URI.')

        user = User().load(doc['userId'], force=True, exc=True)

        # TODO we should record the clients that a user has authorized if we ever make
        # these tokens longer term, i.e. for more than just identity lookup
        token = Token().createToken(user, scope=doc['scope'].split(), days=1)
        token['oauthClientId'] = doc['clientId']

        self.remove(doc)

        return Token().save(token)
