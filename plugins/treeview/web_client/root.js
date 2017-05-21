import _ from 'underscore';

import { children, load } from './types';

export default function (settings = {}) {
    const roots = settings.roots || [{
        id: '#collections',
        type: 'collections'
    }, {
        id: '#users',
        type: 'users'
    }];

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
