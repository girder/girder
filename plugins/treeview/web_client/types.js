import _ from 'underscore';

const definitions = {};

function register(name, load, parent, children, options) {
    definitions[name] = {
        load,
        parent,
        children,
        options
    };
}

function unregister(name) {
    if (!_.has(definitions, name)) {
        delete definitions[name];
        return true;
    }
    return false;
}

function getDefinition(type) {
    if (!_.has(definitions, type)) {
        throw new Error(`Unknown type "${type}"`);
    }
    return definitions[type];
}

function callMethod(doc, method) {
    const def = getDefinition(doc.type);
    if (!_.isFunction(def[method])) {
        throw new Error(`Unknown method "${method}" on type "${doc.type}"`);
    }
    return def[method](doc, def.options);
}

function parent(doc) {
    return callMethod(doc, 'parent');
}

function children(doc) {
    return callMethod(doc, 'children');
}

function load(doc) {
    return callMethod(doc, 'load');
}

export {
    definitions,
    register,
    unregister,
    getDefinition,
    callMethod,
    parent,
    children,
    load
};
