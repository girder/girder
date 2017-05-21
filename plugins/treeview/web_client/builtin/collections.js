import _ from 'underscore';

import { register } from '../types';
import request from '../utils/request';

import * as collection from './collection';

function mutate(doc) {
    return doc;
}

function load(doc) {
    return Promise.resolve({
        id: '#collections',
        parent: '#',
        type: 'collections',
        text: 'Collections',
        children: true
    });
}

function parent(doc) {
    return Promise.resolve(null);
}

function children(doc) {
    return request({
        path: 'collection'
    }).then((collections) => {
        return _.map(collections, collection.mutate);
    });
}

register('collections', load, parent, children);

export {
    load,
    parent,
    children,
    mutate
};
