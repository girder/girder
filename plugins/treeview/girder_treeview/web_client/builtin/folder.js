/**
 * This module defines a series of functions to handle loading
 * folders over Girder's rest interface using a consistent
 * API supported by jstree.
 */

import _ from 'underscore';
import $ from 'jquery';

import { register } from '../types';
import request from '../utils/request';

import * as collection from './collection';
import * as item from './item';
import * as user from './user';

/**
 * Mutate a document returned from Girder's rest api
 * returning a jstree node object.
 */
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

/**
 * Load a folder node from the server.
 */
function load(node) {
    return request({
        path: `folder/${node.id}`
    }).then(mutate);
}

/**
 * Load the folder's parent node from the server.  This
 * automatically determines if the type is a folder, user,
 * or collection and calls the correct load method.
 */
function parent(node) {
    const parentnode = {
        id: node.model.parentId,
        type: node.model.parentCollection
    };

    switch (parentnode.type) {
        case 'folder':
            return load(parentnode);
        case 'user':
            return user.load(parentnode);
        case 'collection':
            return collection.load(parentnode);
        default:
            throw new Error(`Unknown folder parent type "${parentnode.type}"`);
    }
}

/**
 * Load the folder's children from the server.  This has to be
 * done using two requests; one for folders and one for items.
 * The requests are merged together into a single array with
 * folders first.
 */
function children(node) {
    return $.when(...[
        request({
            path: 'folder',
            data: {
                parentId: node.id,
                parentType: 'folder'
            }
        }),
        request({
            path: 'item',
            data: {
                folderId: node.id
            }
        })
    ]).then((folders, items) => {
        return _.map(folders[0], mutate)
            .concat(_.map(items[0], item.mutate));
    });
}

register('folder', {load, parent, children});

export {
    children,
    load,
    mutate,
    parent
};
