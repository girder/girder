import _ from 'underscore';
import 'jstree';
import 'jstree/dist/themes/default/style.css';

import { auth, conditionalselect } from './utils';
import root from './root';
import { model } from './utils/node';
import { icons } from './types';

export default function (el, settings = {}) {
    const selectable = settings.selectable;
    const user = auth();

    return root(settings.root).then((data) => {
        $(el).each(function () {
            settings = $.extend(true, {
                plugins: ['types', 'conditionalselect', 'state'],
                core: {
                    data: data,
                    force_text: true, // prevent XSS
                    themes: {
                        dots: false,
                        responsive: true,
                        stripes: true
                    },
                    multiple: false
                },
                types: _.defaults(icons, {
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
                    },
                    default: {
                        icon: 'icon-doc'
                    }
                }),
                conditionalselect: _.wrap(conditionalselect(selectable), function (func, node) {
                    return func.call(this, model(node), node);
                }),
                state: {
                    key: user.login
                }
            }, settings.jstree);
            $(this).jstree(settings);
        });
    });
}
