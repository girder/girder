import _ from 'underscore';

import { register } from '../types';
import request from '../utils/request';

import * as user from './user';
import * as collection from './collection';
import * as item from './item';

function mutate(folder) {
    return {
        id: folder._id,
        parent: folder.parentId,
        type: 'folder',
        text: folder.name,
        model: folder,
        children: true
    };
}

function load(doc) {
    return request({
        path: `folder/${doc.id}`
    }).then(mutate);
}

function parent(doc) {
    const parentDoc = {
        id: doc.model.parentId,
        type: doc.model.parentCollection
    };

    switch (parentDoc.type) {
        case 'folder':
            return load(parentDoc);
        case 'user':
            return user.load(parentDoc);
        case 'collection':
            return collection.load(parentDoc);
        default:
            throw new Error(`Unknown folder parent type "${parentDoc.type}"`);
    }
}

function children(doc) {
    return Promise.all([
        request({
            path: 'folder',
            data: {
                parentId: doc.id,
                parentType: 'folder'
            }
        }),
        request({
            path: 'item',
            data: {
                folderId: doc.id
            }
        })
    ]).then(([folders, items]) => {
        return _.map(folders, mutate)
            .concat(_.map(items, item.mutate));
    });
}

register('folder', load, parent, children);

export {
    load,
    parent,
    children,
    mutate
};
