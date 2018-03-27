import datetime
import jsonschema
from girder.constants import AccessType
from girder.exceptions import ValidationException
from girder.models.model_base import Model
from girder.models.token import genToken

class Client(Model):
    authSchema = {
        'type': 'array',
        'items': {
            'type': 'string'
        }
    }

    def initialize(self):
        self.name = 'oauth_client'
        self.exposeFields(level=AccessType.SITE_ADMIN, fields={
            '_id', 'authorizedOrigins', 'authorizedRedirects', 'created', 'name', 'secret'
        })

    def validate(self, doc):
        doc['name'] = doc.get('name', '').strip()

        if not doc['name']:
            raise ValidationException('OAuth clients must have a name.')

        try:
            jsonschema.validate(doc.get('authorizedRedirects'), self.authSchema)
        except jsonschema.ValidationError as e:
            raise ValidationException('Invalid authorized redirects: ' + e.message)

        if not doc['authorizedRedirects']:
            raise ValidationException('You must specify at least one authorized redirect URI.')

        try:
            jsonschema.validate(doc.get('authorizedOrigins', []), self.authSchema)
        except jsonschema.ValidationError as e:
            raise ValidationException('Invalid authorized origins: ' + e.message)

        return doc

    def createClient(self, name, authorizedRedirects, authorizedOrigins=None):
        return self.save({
            'name': name,
            'authorizedRedirects': authorizedRedirects,
            'authorizedOrigins': authorizedOrigins or [],
            'created': datetime.datetime.utcnow(),
            'secret': genToken(length=32)
        })
