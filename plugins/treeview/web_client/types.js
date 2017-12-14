import _ from 'underscore';
import $ from 'jquery';

/**
 * A registry for type definitions.
 */
const definitions = {};

/**
 * A registry for node aliases.  An alias is a way to move a node
 * to different place in the tree.  Currently, this is only used
 * for the "Home" type, which is an alias of the currently logged
 * in user.  Another possible use case is to create a list of
 * "favorite" locations that appear in a their own branch of
 * the tree.
 */
const aliases = {};

/**
 * A registry of icon classes used by registered types.  These
 * are provided to the jstree constructor extending the default
 * icons.
 */
const icons = {};

const defaultChildren = _.constant($.Deferred().resolve([]).promise());
const defaultParent = _.constant($.Deferred().resolve(null).promise());

/**
 * Register a new node type.
 *
 * @param {string} name The unique name of the type.
 *
 * @param {object} def
 *   The type definition.  This is a mapping to a set of standard
 *   functions telling the tree object how to handle specific operations
 *   on the nodes.
 *
 * @param {function} def.load
 *   Load a node from the server.  This is typically an ajax request
 *   to the girder rest API.  It will receive a partial node object
 *   with an `id` field and should return a promise that resolves to
 *   the full node object expected by jstree.
 *
 * @param {function} [def.parent]
 *   Load the parent of the provided node.  This is similar to the
 *   `load` method, but it should provide the parent node instead.
 *   This is optional for root types with no parents.
 *
 * @param {function} [def.children]
 *   Load the children of the provided node.  This should return
 *   a promise that resolves to a list of child nodes.  For leaf
 *   types, this is optional.
 *
 * @param {object} [def.options={}]
 *   An optional object that will be passed to all loading methods.
 *   This is intended for internal use by the individual types.
 *
 * @param {string} [def.icon]
 *   A fontello icon class that will be displayed next to the node.
 */
function register(name, def) {
    def = def || {};
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

/**
 * Remove a type definition from the registry.
 *
 * @param {string} name The name of the type to remove.
 * @returns {object} The definition of the type that was removed.
 */
function unregister(name) {
    const def = definitions[name];
    delete definitions[name];
    return def;
}

/**
 * Create a new type alias.
 *
 * @param {string} id The id of the aliased node.
 * @param {string} type The type the node is aliased to.
 */
function alias(id, type) {
    aliases[id] = type;
}

/**
 * Remove a type alias.
 *
 * @param {string} id The id of the node to remove.
 * @returns {string} The original type alias.
 */
function unalias(id) {
    const type = aliases[id];
    delete aliases[id];
    return type;
}

/**
 * Return if a node is aliased as a different type.
 * @param {object} node
 * @returns {boolean}
 */
function isAliased(node) {
    return aliases[node.id] && aliases[node.id] !== node.type;
}

/**
 * Return the definition object for a type.
 *
 * @param {string} type The type name.
 * @throws Will throw if the type is not defined.
 * @returns {object} The type definition.
 */
function getDefinition(type) {
    if (!_.has(definitions, type)) {
        throw new Error(`Unknown type "${type}"`);
    }
    return definitions[type];
}

/**
 * For future use to generate a context menu on a node.
 * @private
 */
function contextMenu(node) {
    const def = getDefinition(node.type);
    const menu = def.contextmenu;
    if (_.isFunction(menu)) {
        return menu(node);
    }
    return menu;
}

/**
 * Call a method from a type definition on node.
 *
 * @param {object} node
 * @param {string} method
 * @throws Will throw if the method is not defined for the type.
 * @returns {*} The result of the method.
 */
function callMethod(node, method) {
    const def = getDefinition(node.type);
    if (!_.isFunction(def[method])) {
        throw new Error(`Unknown method "${method}" on type "${node.type}"`);
    }
    return def[method](node, def.options);
}

/**
 * Get the parent of a node by dispatching to the type's `parent`
 * method.
 *
 * @param {object} node
 * @returns {Promise} Resolves to the parent node.
 */
function parent(node) {
    return callMethod(node, 'parent')
        .then((node) => {
            if (!node) {
                return node;
            }

            if (isAliased(node)) {
                node.type = aliases[node.id];
            }
            return node;
        });
}

/**
 * Get the children of a node by dispatching to the type's `children`
 * method.
 *
 * @param {object} node
 * @returns {Promise} Resolves to an array of child nodes.
 */
function children(node) {
    return callMethod(node, 'children')
        .then((children) => {
            return _.reject(children, isAliased);
        });
}

/**
 * Get a node by dispatching to the type's `load` method.
 *
 * @param {object} node
 * @returns {Promise} Resolves to the value of the node.
 */
function load(node) {
    return callMethod(node, 'load')
        .then((node) => {
            if (isAliased(node)) {
                node.type = aliases[node.id];
            }
            return node;
        });
}

export {
    alias,
    callMethod,
    children,
    contextMenu,
    definitions,
    getDefinition,
    icons,
    isAliased,
    load,
    parent,
    register,
    unalias,
    unregister
};
