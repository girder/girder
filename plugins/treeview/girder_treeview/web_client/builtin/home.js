/**
 * This module defines a builtin `home` node type.  This
 * type is an alias of the current user to display the
 * user's home folders more prominently.
 */

import { register } from '../types';

import * as user from './user';

/**
 * Mutate a user node or document into a `home` node.
 */
function mutate(doc) {
    return {
        id: doc._id || doc.id,
        parent: '#',
        type: 'home',
        text: 'Home',
        model: doc,
        children: true
    };
}

/**
 * Load the home node from the server by calling the
 * user `load` method.
 */
function load(node) {
    return user.load(node)
        .then(mutate);
}

/**
 * Get a list of all folders under the current user.
 */
function children(node) {
    return user.children(node);
}

register('home', {load, children});

export {
    children,
    load,
    mutate
};
