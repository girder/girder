/**
 * This module defines a series of functions to handle loading
 * items over Girder's rest interface using a consistent
 * API supported by jstree.
 */

import _ from 'underscore';

import { register } from '../types';
import request from '../utils/request';

import * as file from './file';
import * as folder from './folder';

/**
 * Mutate a document returned from Girder's rest api
 * returning a jstree node object.
 */
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

/**
 * Load an item node from the server.
 */
function load(node) {
    return request({
        path: `item/${node.id}`
    }).then(mutate);
}

/**
 * Load the item's parent folder from the server.
 */
function parent(node) {
    return folder.load({
        id: node.model.folderId,
        type: 'folder'
    });
}

/**
 * Load all files contained in an item from the server.
 */
function children(node) {
    return request({
        path: `item/${node.id}/files`
    }).then((files) => {
        return _.map(files, file.mutate);
    });
}

register('item', {load, parent, children});

export {
    children,
    load,
    mutate,
    parent
};
