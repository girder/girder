/* global process */

// Default value for external builds
let version = null;

try {
    version = import.meta.env.VITE_GIRDER_VERSION || null;
} catch (e) {}

export default version;
