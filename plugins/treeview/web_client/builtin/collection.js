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

function create(data) {
    const inst = $.jstree.reference(data.reference);
    const node = inst.get_node(data.reference);

    inst.create_node(node, {type: 'folder', id: 'derp'}, 'last', (newNode) => {
        inst.edit(newNode);
    });
}

function contextmenu(node) {
    return {
        create: {
            label: 'Create folder',
            action: create
        }
    };
}

register('collection', load, parent, children, {contextmenu});

export {
    load,
    parent,
    children,
    mutate
};
