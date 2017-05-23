import _ from 'underscore';
import 'jstree';
import 'jstree/dist/themes/default/style.css';

import { auth, conditionalselect } from './utils';
import root from './root';
import { model } from './utils/node';
import { icons, contextMenu } from './types';

export default function (el, settings = {}) {
    const selectable = settings.selectable;
    const user = auth();
    const selectableFunc = _.wrap(conditionalselect(selectable), function (func, node) {
        return func.call(this, model(node), node);
    });

    return root(settings.root).then((data) => {
        $(el).each(function () {
            const reselectNodes = () => {
                const jstree = $(this).jstree(true);
                const nodes = _.filter(
                    jstree.get_selected(true),
                    selectableFunc
                );
                jstree.deselect_all();

                // do the reselection after the load event
                window.setTimeout(() => {
                    jstree.select_node(nodes);
                }, 0);
            };

            settings = $.extend(true, {
                plugins: ['types', 'conditionalselect', 'state', 'contextmenu'],
                core: {
                    data: data,
                    force_text: true, // prevent XSS
                    themes: {
                        dots: false,
                        responsive: true,
                        stripes: true
                    },
                    multiple: false,
                    check_callback: true
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
                conditionalselect: selectableFunc,
                state: {
                    key: user.login
                },
                contextmenu: {
                    items: contextMenu
                }
            }, settings.jstree);

            $(this).one('state_ready.jstree', reselectNodes).jstree(settings);
        });
    });
}
