import abc


class Transform(metaclass=abc.ABCMeta):
    def _repr_model_(self):
        """Return as representation of the object suitable for storing in mongo.

        This function returns a string representation of the object
        that is stored in a girder Job Model's 'args' or 'kwargs'
        fields.  It is for display purposes only.

        """
        return str(self)

    def cleanup(self):
        pass

    @abc.abstractmethod
    def transform(self):
        pass


class ResultTransform(Transform, metaclass=abc.ABCMeta):
    # This will be populated by the worker via the girder_before_task_publish hook,
    # and it will point to the job that was created for this task. If no job was created
    # for this task, this will remain `None`.
    job = None

    @abc.abstractmethod
    def transform(self, data):
        pass

    def exception(self):
        pass
