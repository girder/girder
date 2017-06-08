import _ from 'underscore';
import $ from 'jquery';

import auth from './utils/auth';
import { children, load, alias } from './types';

export default function (settings = {}) {
    const user = auth();
    const roots = settings.roots || [{
        id: '#collections',
        type: 'collections'
    }, {
        id: '#users',
        type: 'users'
    }];

    if (user) {
        roots.splice(0, 0, {
            id: user._id,
            type: 'home'
        });
        alias(user._id, 'home');
    }

    return $.when(..._.map(roots, load))
        .then((...rootDocs) => {
            return function (node, cb) {
                if (node.id === '#') {
                    cb(rootDocs);
                } else {
                    children(node.original).then(cb);
                }
            };
        });
}
