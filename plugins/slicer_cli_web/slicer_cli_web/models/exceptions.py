class DockerImageError(Exception):
    def __init__(self, message, image_name='None'):  # noqa: B042

        self.message = message
        # can be a string or list
        self.imageName = image_name
        super().__init__(message)

    def __str__(self):
        if isinstance(self.imageName, list):
            return self.message + ' (image names [' + ','.join(self.imageName) + '])'
        elif isinstance(self.imageName, str):
            return self.message + ' (image name: ' + self.imageName + ')'
        else:
            return self.message


class DockerImageNotFoundError(DockerImageError):
    def __init__(self, message, image_name, locations=None):  # noqa: B042
        super().__init__(message, image_name)
        # list of registries tried(local dockerhub etc )
        self.locations = locations or []
