class GirderBaseException(Exception):
    """
    A class from which all Girder exceptions are based.
    """

    pass


class AccessException(GirderBaseException):
    """
    Represents denial of access to a resource.
    """

    def __init__(self, message, extra=None):
        self.message = message
        self.extra = extra

        super().__init__(message)


class GirderException(GirderBaseException):
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

        super().__init__(message)


class NoAssetstoreAdapter(GirderException):
    """
    Raised when no assetstore adapter is available.
    """

    identifier = 'girder.utility.assetstore.no-adapter'

    def __init__(self, message='No assetstore adapter'):
        super().__init__(message, self.identifier)


class ValidationException(GirderBaseException):
    """
    Represents validation failure in the model layer. Raise this with
    a message and an optional field property. If one of these is thrown
    in the model during a REST request, it will respond as a 400 status.
    """

    def __init__(self, message, field=None):
        self.field = field
        self.message = message

        super().__init__(message)


class ResourcePathNotFound(ValidationException):
    """
    A special case of ValidationException representing the case when the resource at a
    given path does not exist.
    """

    pass


class RestException(GirderBaseException):
    """
    Throw a RestException in the case of any sort of incorrect
    request (i.e. user/client error). Login and permission failures
    should set a 403 code; almost all other validation errors
    should use status 400, which is the default.
    """

    def __init__(self, message, code=400, extra=None):
        self.code = code
        self.extra = extra
        self.message = message

        super().__init__(message)


class FilePathException(GirderException):
    """
    Thrown when a file path is requested and cannot be returned.
    """

    identifier = 'girder.utility.assetstore.file-path-not-available'

    def __init__(self, message='No assetstore adapter', identifier=None):
        super().__init__(message, identifier or self.identifier)
