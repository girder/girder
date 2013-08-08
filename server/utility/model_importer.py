import importlib

class ModelImporter(object):
    """
    Any class that wants to have convenient model importing semantics
    should extend/mixin this class.
    """
    def __init__(self):
        self._requiredModels = []

    def requireModels(self, modelList):
        """
        Subclasses should call this to instantiate models members on themselves.
        :param modelList: The list of models that should be instantiated as members.
        For example, if the returned list contains 'user', it will set self.userModel.
        The values in the list should either be strings (e.g. 'user') or if necessary
        due to naming conventions, a 2-tuple of the form ('model_module_name', 'ModelClassName').
        :type modelList: list of str
        """
        assert type(modelList) is list

        for model in modelList:
            if type(model) is str:
                # Default transform is e.g. 'user' -> 'User()'
                modelName = model
                className = model[0].upper() + model[1:]
            elif type(model) is tuple:
                # Custom class name e.g. 'some_thing' -> 'SomeThing()'
                modelName = model[0]
                className = model[1]
            else:
                raise Exception('Required models should be strings or tuples.')

            if hasattr(self, '%sModel' % modelName): # we already have this model
                continue

            try:
                imported = importlib.import_module('models.%s' % modelName)
            except ImportError:
                raise Exception('Could not load model module "%s"' % modelName)

            try:
                constructor = getattr(imported, className)
            except AttributeError:
                raise Exception('Incorrect model class name "%s" for model "%s"' %
                                (className, modelName))
            setattr(self, '%sModel' % modelName, constructor())


