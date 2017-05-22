import _ from 'underscore';

const definitions = {};
const aliases = {};
const icons = {};

function register(name, load, parent, children, options = {}) {
    definitions[name] = {
        load,
        parent,
        children,
        options
    };
    if (options.icon) {
        icons[name] = {
            icons: options.icon
        };
    }
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
    const menu = def.options.contextmenu;
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
