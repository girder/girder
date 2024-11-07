from .girder import Girder


class GirderItem(Girder):
    """Define a parameter representing a girder item id."""

    def describe(self, **kwargs):
        desc = super().describe(**kwargs)
        desc['type'] = 'file'
        desc['description'] = self.help or 'Select an item'
        return desc
