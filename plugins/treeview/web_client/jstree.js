import 'jstree';
import 'jstree/dist/themes/default/style.css';
import _ from 'underscore';

import { contextMenu, icons } from './types';
import { auth } from './utils';
import { model } from './utils/node';
import root from './root';

/**
 * This is a helper function to unify the behavior of the
 * `selectable` setting in the jstree constructor.
 *
 *    * If the argument is an array, it returns true if the model
 *      type is one of the elements of the string.
 *    * If the argument is a function, the model is passed to that
 *      function.
 *    * Otherwise, the node is selectable if it is derived from a
 *      girder model.
 */
function conditionalselect(selectable) {
    if (_.isFunction(selectable)) {
        return selectable;
    }

    if (_.isArray(selectable)) {
        return function (model) {
            return model && _.contains(selectable, model._modelType);
        };
    }

    return function (model) {
        return model;
    };
}

/**
 * Initialize a jstree object on the given element.
 *
 * @param {HTMLElement} el The DOM element to attach to
 *
 * @param {object} [settings={}] An optional settings object
 * @param {string[]|function} [settings.selectable]
 *   An array of selectable node types.  This can also be a function
 *   that takes the node as an argument and returns a boolean indicating
 *   if the node is selectable.
 *
 * @param {object[]} [settings.root]
 *   The root nodes of the tree object. See {@link root}.
 *
 * @param {object} [settings.jstree]
 *   Additional settings to pass to the jstree constructor.
 *
 * @returns {Promise}
 *   Resolves after the jstree object is constructed.
 */
export default function (el, settings = {}) {
    const selectable = settings.selectable;
    const user = auth();
    const selectableFunc = _.wrap(conditionalselect(selectable), function (func, node) {
        return func.call(this, model(node), node);
    });

    return root(settings.root).then((data) => {
        return $(el).each(function () {
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
                plugins: ['types', 'conditionalselect', 'state'],
                core: {
                    data: data,
                    force_text: true, // prevent XSS
                    themes: {
                        dots: false,
                        responsive: true,
                        stripes: true
                    },
                    multiple: false,
                    check_callback: false,
                    worker: true // use webworkers (false is helpful for debugging)
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
                    key: user ? user.login : 'anonymous'
                },
                contextmenu: {
                    items: contextMenu
                }
            }, settings.jstree);

            $(this).one('state_ready.jstree', reselectNodes).jstree(settings);
        });
    });
}
