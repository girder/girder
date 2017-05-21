import { register } from '../types';
import request from '../utils/request';

import * as item from './item';

function mutate(file) {
    return {
        id: file._id,
        parent: file.itemId,
        type: 'file',
        text: file.name,
        model: file
    };
}

function load(doc) {
    return request({
        path: `file/${doc.id}`
    }).then(mutate);
}

function parent(doc) {
    return item.load({
        id: doc.model.itemId,
        type: 'item'
    });
}

function children(doc) {
    return Promise.resolve([]);
}

register('file', load, parent, children);

export {
    load,
    parent,
    children,
    mutate
};
