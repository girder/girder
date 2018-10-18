/**
 * Expose the symbols for a girder plugin under the window.girder.plugins
 * namespace. Required since each plugin is loaded dynamically.
 */
var registerPluginNamespace = function (pluginName, symbols) {
    window.girder.plugins[pluginName] = symbols;
};

export {
    registerPluginNamespace
};
