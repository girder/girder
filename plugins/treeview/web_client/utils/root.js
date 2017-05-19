import * as children from '../children';

export default function (settings = {}) {
    const roots = settings.roots || [{
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

    if (settings.user) {
        roots.splice(0, 0, {
            id: settings.user._id,
            parent: '#',
            type: 'home',
            text: 'Home',
            children: true,
            model: settings.user
        });
    }
    return function (node, cb) {
        if (node.id === '#') {
            cb(roots);
        } else {
            children[node.type](node.original.model)
                .then(cb);
        }
    };
}
