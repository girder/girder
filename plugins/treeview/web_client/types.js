import _ from 'underscore';
import $ from 'jquery';

const definitions = {};
const aliases = {};
const icons = {};

const defaultChildren = _.constant($.Deferred().resolve([]).promise());
const defaultParent = _.constant($.Deferred().resolve(null).promise());

function register(name, def = {}) {
    if (!_.isFunction(def.load)) {
        throw new Error('Node types require a load method');
    }

    if (def.icon) {
        icons[name] = {
            icons: def.icon
        };
    }

    definitions[name] = _.defaults(def, {
        children: defaultChildren,
        parent: defaultParent,
        options: {}
    });
}

function unregister(name) {
    const def = definitions[name];
    delete definitions[name];
    return def;
}

function alias(id, type) {
    aliases[id] = type;
}

function unalias(id) {
    const type = aliases[id];
    delete aliases[id];
    return type;
}

function isAliased(doc) {
    return aliases[doc.id] && aliases[doc.id] !== doc.type;
}

function getDefinition(type) {
    if (!_.has(definitions, type)) {
        throw new Error(`Unknown type "${type}"`);
    }
    return definitions[type];
}

function contextMenu(node) {
    const def = getDefinition(node.type);
    const menu = def.contextmenu;
    if (_.isFunction(menu)) {
        return menu(node);
    }
    return menu;
}

function callMethod(doc, method) {
    const def = getDefinition(doc.type);
    if (!_.isFunction(def[method])) {
        throw new Error(`Unknown method "${method}" on type "${doc.type}"`);
    }
    return def[method](doc, def.options);
}

function parent(doc) {
    return callMethod(doc, 'parent')
        .then((doc) => {
            if (!doc) {
                return doc;
            }

            if (isAliased(doc)) {
                doc.type = aliases[doc.id];
            }
            return doc;
        });
}

function children(doc) {
    return callMethod(doc, 'children')
        .then((children) => {
            return _.reject(children, isAliased);
        });
}

function load(doc) {
    return callMethod(doc, 'load')
        .then((doc) => {
            if (isAliased(doc)) {
                doc.type = aliases[doc.id];
            }
            return doc;
        });
}

export {
    definitions,
    register,
    unregister,
    alias,
    unalias,
    isAliased,
    getDefinition,
    callMethod,
    contextMenu,
    parent,
    children,
    load,
    icons
};
