/**
 * This module defines a series of functions to handle loading
 * files over Girder's rest interface using a consistent
 * API supported by jstree.
 */

import { register } from '../types';
import request from '../utils/request';

import * as item from './item';

/**
 * Mutate a document returned from Girder's rest api
 * returning a jstree node object.
 */
function mutate(file) {
    return {
        id: file._id,
        parent: file.itemId,
        type: 'file',
        text: file.name,
        model: file
    };
}

/**
 * Load a file node from the server.
 */
function load(node) {
    return request({
        path: `file/${node.id}`
    }).then(mutate);
}

/**
 * Load a file's item from the server.
 */
function parent(node) {
    return item.load({
        id: node.model.itemId,
        type: 'item'
    });
}

register('file', {load, parent});

export {
    load,
    mutate,
    parent
};
