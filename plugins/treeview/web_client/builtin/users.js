import _ from 'underscore';
import $ from 'jquery';

import { register } from '../types';
import request from '../utils/request';

import * as user from './user';

function mutate(doc) {
    return doc;
}

function load(doc) {
    return $.Deferred().resolve({
        id: '#users',
        parent: '#',
        type: 'users',
        text: 'Users',
        children: true
    }).promise();
}

function children(doc) {
    return request({
        path: 'user'
    }).then((users) => {
        return _.map(users, user.mutate);
    });
}

register('users', {load, children});

export {
    load,
    children,
    mutate
};
