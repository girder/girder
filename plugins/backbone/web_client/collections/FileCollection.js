import { apiRoot } from 'girder/rest';

import Collection from './Collection';
import FileModel from '../models/FileModel';

const FileCollection = Collection.extend({
    resource: 'file',
    model: FileModel,
    url() {
        return `${apiRoot}/item/${this.parent.id}/files`;
    }
});

export default FileCollection;
