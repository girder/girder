from .girder import Girder


class GirderFolder(Girder):
    """Define a parameter representing a girder folder id."""

    def describe(self, **kwargs):
        desc = super().describe(**kwargs)
        desc['type'] = 'directory'
        desc['description'] = self.help or 'Select a folder'
        return desc
