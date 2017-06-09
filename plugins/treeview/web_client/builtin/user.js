/**
 * This module defines a series of functions to handle loading
 * users over Girder's rest interface using a consistent
 * API supported by jstree.
 */

import _ from 'underscore';

import { register } from '../types';
import request from '../utils/request';

import * as folder from './folder';
import * as users from './users';

/**
 * Mutate a document returned from Girder's rest api
 * returning a jstree node object.
 */
function mutate(user) {
    return {
        id: user._id,
        parent: '#users',
        type: 'user',
        text: user.login,
        model: user,
        children: true
    };
}

/**
 * Load a user node from the server.
 */
function load(node) {
    return request({
        path: `user/${node.id}`
    }).then(mutate);
}

/**
 * Load the user's parent using the `users` load method.
 */
const parent = users.load;

/**
 * Load a user's folders from the server.
 */
function children(node) {
    return request({
        path: 'folder',
        data: {
            parentId: node.id,
            parentType: 'user'
        }
    }).then((folders) => {
        return _.map(folders, folder.mutate);
    });
}

register('user', {load, parent, children});

export {
    children,
    load,
    mutate,
    parent
};
