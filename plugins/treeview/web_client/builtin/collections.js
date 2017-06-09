/**
 * This module defines a builtin `collections` node type.  This
 * type is not reflected in Girder's API, but only exists as a
 * container to hold all collections that exist on the server.
 */

import _ from 'underscore';
import $ from 'jquery';

import { register } from '../types';
import request from '../utils/request';

import * as collection from './collection';

/**
 * For consistency with out builtin types, define a mutate
 * method that is a no-op.
 */
function mutate(node) {
    return node;
}

/**
 * Define the unique node representing the `collections` type.
 */
function load(node) {
    return $.Deferred().resolve({
        id: '#collections',
        parent: '#',
        type: 'collections',
        text: 'Collections',
        children: true
    }).promise();
}

/**
 * Get a list of all collections on the server.
 */
function children(node) {
    return request({
        path: 'collection'
    }).then((collections) => {
        return _.map(collections, collection.mutate);
    });
}

register('collections', {load, children});

export {
    children,
    load,
    mutate
};
