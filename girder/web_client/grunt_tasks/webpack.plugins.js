/**
 * This file contains custom webpack plugins.
 */
'use strict';

// This plugin modifies the generated webpack code to execute a module within the DLL bundle
// in addition to preserving the default behavior of exporting the webpack require function
class DllBootstrapPlugin {
    constructor(options) {
        this.options = options || {};
    }

    apply(compiler) {
        compiler.plugin('compilation', (compilation) => {
            compilation.mainTemplate.plugin('startup', (source, chunk) => {
                const bootstrapEntry = this.options[chunk.name];
                if (bootstrapEntry) {
                    const module = chunk.modules.find((m) => m.rawRequest === bootstrapEntry);
                    source = `__webpack_require__(${module.id});\n${source}`;
                }
                return source;
            });
        });
    }
}

module.exports = {
    DllBootstrapPlugin
};
