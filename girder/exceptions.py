class AccessException(Exception):
    """
    Represents denial of access to a resource.
    """
    def __init__(self, message, extra=None):
        self.message = message
        self.extra = extra

        Exception.__init__(self, message)


class GirderException(Exception):
    """
    Represents a general exception that might occur in regular use.  From the
    user perspective, these are failures, but not catastrophic ones.  An
    identifier can be passed, which allows receivers to check the exception
    without relying on the text of the message.  It is recommended that
    identifiers are a dot-separated string consisting of the originating
    python module and a distinct error.  For example,
    'girder.model.assetstore.no-current-assetstore'.
    """
    def __init__(self, message, identifier=None):
        self.identifier = identifier
        self.message = message

        Exception.__init__(self, message)


class NoAssetstoreAdapter(GirderException):
    """
    Raised when no assetstore adapter is available.
    """
    identifier = 'girder.utility.assetstore.no-adapter'

    def __init__(self, message='No assetstore adapter'):
        return super(NoAssetstoreAdapter, self).__init__(message, self.identifier)


class ValidationException(Exception):
    """
    Represents validation failure in the model layer. Raise this with
    a message and an optional field property. If one of these is thrown
    in the model during a REST request, it will respond as a 400 status.
    """
    def __init__(self, message, field=None):
        self.field = field
        self.message = message

        Exception.__init__(self, message)
