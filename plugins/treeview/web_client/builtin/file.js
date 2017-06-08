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

register('file', {load, parent});

export {
    load,
    parent,
    mutate
};
