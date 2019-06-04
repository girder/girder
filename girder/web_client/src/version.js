/* global process */

// Default value for external builds
let version = null;

try {
    version = process.env.GIRDER_VERSION || null;
} catch (e) {}

export default version;
