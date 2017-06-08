import _ from 'underscore';

import { register } from '../types';
import request from '../utils/request';

import * as collections from './collections';
import * as folder from './folder';

function mutate(collection) {
    return {
        id: collection._id,
        parent: '#collections',
        type: 'collection',
        text: collection.name,
        model: collection,
        children: true
    };
}

function load(doc) {
    return request({
        path: `collection/${doc.id}`
    }).then(mutate);
}

const parent = function () {
    return collections.load.apply(this, arguments);
};

function children(doc) {
    return request({
        path: 'folder',
        data: {
            parentId: doc.id,
            parentType: 'collection'
        }
    }).then((folders) => {
        return _.map(folders, folder.mutate);
    });
}

register('collection', {load, parent, children});

export {
    load,
    parent,
    children,
    mutate
};
