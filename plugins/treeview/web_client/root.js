import getCurrentUser from './auth';

import * as children from './children';

export default function () {
    const user = getCurrentUser();
    const root = [{
        id: '#collections',
        parent: '#',
        type: 'collections',
        text: 'Collections',
        children: true
    }, {
        id: '#users',
        parent: '#',
        type: 'users',
        text: 'Users',
        children: true
    }];

    if (user) {
        root.splice(0, 0, {
            id: user._id,
            parent: '#',
            type: 'home',
            text: 'Home',
            children: true,
            model: user
        });
    }
    return function (node, cb) {
        if (node.id === '#') {
            cb(root);
        } else {
            children[node.type](node.original.model)
                .then(cb);
        }
    };
}
