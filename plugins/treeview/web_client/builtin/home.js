import { register } from '../types';

import * as user from './user';

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

function load(doc) {
    return user.load(doc)
        .then(mutate);
}

function parent(doc) {
    return Promise.resolve(null);
}

function children(doc) {
    return user.children(doc);
}

register('home', load, parent, children);

export {
    load,
    parent,
    children,
    mutate
};
