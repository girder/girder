import _ from 'underscore';

import { register } from '../types';
import request from '../utils/request';

import * as folder from './folder';
import * as file from './file';

function mutate(item) {
    return {
        id: item._id,
        parent: item.folderId,
        type: 'item',
        text: item.name,
        model: item,
        children: true
    };
}

function load(doc) {
    return request({
        path: `item/${doc.id}`
    }).then(mutate);
}

function parent(doc) {
    return folder.load({
        id: doc.model.folderId,
        type: 'folder'
    });
}

function children(doc) {
    return request({
        path: `item/${doc.id}/files`
    }).then((files) => {
        return _.map(files, file.mutate);
    });
}

register('item', {load, parent, children});

export {
    load,
    parent,
    children,
    mutate
};
