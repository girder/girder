import _ from 'underscore';

import { register } from '../types';
import request from '../utils/request';

import * as users from './users';
import * as folder from './folder';

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

function load(doc) {
    return request({
        path: `user/${doc.id}`
    }).then(mutate);
}

const parent = users.load;

function children(doc) {
    return request({
        path: 'folder',
        data: {
            parentId: doc.id,
            parentType: 'user'
        }
    }).then((folders) => {
        return _.map(folders, folder.mutate);
    });
}

register('user', load, parent, children);

export {
    load,
    parent,
    children,
    mutate
};
