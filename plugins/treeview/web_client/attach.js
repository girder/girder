import _ from 'underscore';
import 'jstree';
import 'jstree/dist/themes/default/style.css';

import { root, auth, conditionalselect } from './utils';

export default function (el, settings = {}) {
    const selectable = settings.selectable;

    $(el).each(function () {
        settings = $.extend(true, {
            plugins: ['types', 'conditionalselect'],
            core: {
                data: root(_.defaults(settings.root || {}, {user: auth()})),
                force_text: true // prevent XSS
            },
            types: {
                folder: {
                    icon: 'icon-folder'
                },
                item: {
                    icon: 'icon-doc-text-inv'
                },
                user: {
                    icon: 'icon-user'
                },
                collection: {
                    icon: 'icon-globe'
                },
                users: {
                    icon: 'icon-users'
                },
                home: {
                    icon: 'icon-home'
                },
                collections: {
                    icon: 'icon-sitemap'
                },
                file: {
                    icon: 'icon-doc-inv'
                }
            },
            conditionalselect: _.wrap(conditionalselect(selectable), function (func, node) {
                return func.call(this, node.original.model, node);
            })
        }, settings.jstree);
        $(this).jstree(settings);
    });
}
