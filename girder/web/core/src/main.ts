import { girder } from '@girder/core';

const apiRoot = import.meta.env.API_ROOT ?? '/api/v1';
girder.initializeDefaultApp(apiRoot);
