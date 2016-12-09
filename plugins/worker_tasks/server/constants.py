from girder.constants import TokenScope

ACCESS_FLAG_EXECUTE_TASK = 'worker_tasks.execute'
TOKEN_SCOPE_EXECUTE_TASK = 'worker_tasks.execute'

TokenScope.describeScope(
    TOKEN_SCOPE_EXECUTE_TASK, name='Execute tasks', description='Execute tasks in the worker.')
