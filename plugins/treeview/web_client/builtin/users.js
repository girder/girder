/**
 * This module defines a builtin `users` node type.  This
 * type is not reflected in Girder's API, but only exists as a
 * container to hold all users that exist on the server.
 */

import _ from 'underscore';
import $ from 'jquery';

import { register } from '../types';
import request from '../utils/request';

import * as user from './user';

/**
 * For consistency with out builtin types, define a mutate
 * method that is a no-op.
 */
function mutate(node) {
    return node;
}

/**
 * Define the unique node representing the `users` type.
 */
function load(node) {
    return $.Deferred().resolve({
        id: '#users',
        parent: '#',
        type: 'users',
        text: 'Users',
        children: true
    }).promise();
}

/**
 * Get a list of all users on the server.
 */
function children(node) {
    return request({
        path: 'user'
    }).then((users) => {
        return _.map(users, user.mutate);
    });
}

register('users', {load, children});

export {
    children,
    load,
    mutate
};
