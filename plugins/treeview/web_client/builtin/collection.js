/**
 * This module defines a series of functions to handle loading
 * collections over Girder's rest interface using a consistent
 * API supported by jstree.
 */

import _ from 'underscore';

import { register } from '../types';
import request from '../utils/request';

import * as collections from './collections';
import * as folder from './folder';

/**
 * Mutate a document returned from Girder's rest api
 * returning a jstree node object.
 */
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

/**
 * Load a collection node from the server.
 */
function load(node) {
    return request({
        path: `collection/${node.id}`
    }).then(mutate);
}

/**
 * Load the collection's parent using the `collections`
 * load method.
 */
const parent = function () {
    return collections.load.apply(this, arguments);
};

/**
 * Load a collection's children from the server.
 */
function children(node) {
    return request({
        path: 'folder',
        data: {
            parentId: node.id,
            parentType: 'collection'
        }
    }).then((folders) => {
        return _.map(folders, folder.mutate);
    });
}

register('collection', {load, parent, children});

export {
    children,
    load,
    mutate,
    parent
};
