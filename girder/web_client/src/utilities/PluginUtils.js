import _ from 'underscore';

/**
 * Wrap the prototype method of a given object.
 *
 * @param obj The object whose prototype to extend, e.g. MyView
 * @param funcName The name of the function to wrap, e.g. "render"
 * @param wrapper The wrapper function, which should be a function taking the
 *     underlying wrapped function as its first argument. The wrapped function
 *     should be called with .call(this[, arguments]) inside of the wrapper in
 *     order to preserve "this" semantics.
 */
function wrap(obj, funcName, wrapper) {
    obj.prototype[funcName] = _.wrap(obj.prototype[funcName], wrapper);
}

var _pluginConfigRoutes = {};

/**
 * Expose a plugin configuration page via the admin plugins page.
 * @param pluginName The canonical plugin name, i.e. its directory name
 * @param route The route to trigger that will render the plugin config.
 */
function exposePluginConfig(pluginName, route) {
    _pluginConfigRoutes[pluginName] = route;
}

function getPluginConfigRoute(pluginName) {
    return _pluginConfigRoutes[pluginName];
}

export {
    exposePluginConfig,
    getPluginConfigRoute,
    wrap
};
