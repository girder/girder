import _ from 'underscore';

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

    return Promise.all(_.map(roots, load))
        .then((rootDocs) => {
            return function (node, cb) {
                if (node.id === '#') {
                    cb(rootDocs);
                } else {
                    children(node.original).then(cb);
                }
            };
        });
}
