/**
 * This file contains custom webpack plugins.
 */

var _ = require('underscore');
var webpack = require('webpack');

/**
 * We wrap the normal DllReferencePlugin to be able to accept a path to a manifest file
 * rather than its contents. This is because at grunt config time, the manifest
 * file may not exist yet, so we need to defer reading the file until task runtime.
 */
var DllReferenceByPathPlugin = function (options) {
    // called at config time
    webpack.DllReferencePlugin.call(this, options);
};

DllReferenceByPathPlugin.prototype.apply = function (compiler) {
    // called at runtime
    if (_.isString(this.options.manifest)) {
        this.options.manifest = require(this.options.manifest);
    }

    webpack.DllReferencePlugin.prototype.apply.call(this, compiler);
};

module.exports = {
    DllReferenceByPathPlugin
};
