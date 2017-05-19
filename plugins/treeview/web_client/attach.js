import _ from 'underscore';
import 'jstree';
import 'jstree/dist/themes/default/style.css';

import { root, auth, conditionalselect } from './utils';
import { model } from './utils/node';

export default function (el, settings = {}) {
    const selectable = settings.selectable;
    const user = auth();

    $(el).each(function () {
        settings = $.extend(true, {
            plugins: ['types', 'conditionalselect', 'state'],
            core: {
                data: root(_.defaults(settings.root || {}, {user})),
                force_text: true, // prevent XSS
                themes: {
                    dots: false,
                    responsive: true,
                    stripes: true
                }
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
                return func.call(this, model(node), node);
            }),
            state: {
                key: user.login
            }
        }, settings.jstree);
        $(this).jstree(settings);
    });
}
