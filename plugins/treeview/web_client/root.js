import _ from 'underscore';
import $ from 'jquery';

import { alias, children, load } from './types';
import auth from './utils/auth';

/**
 * Generate a tree construction function to pass into jstree.
 *
 * @param {object} [settings={}] Optional settings object
 * @param {object[]} [settings.root]
 *   Describes the root nodes to generate.  Defaults to
 *   "Collections", "Users", and "Home".
 *
 * @returns {Promise}
 *   A promise that resolves to a lazy-loading function compatible
 *   with jstree:
 *     https://github.com/vakata/jstree#populating-the-tree-using-a-callback-function
 */
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
                    children(node.original).then(cb); // eslint-disable-line promise/no-nesting
                }
            };
        });
}
