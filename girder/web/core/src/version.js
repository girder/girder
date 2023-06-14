/* global process */

// Default value for external builds
let versionRaw = null;

try {
    versionRaw = process.env.GIRDER_VERSION || null;
} catch (e) {}

// Enforce that it's a string or null to make TypeScript happy
const version = versionRaw === null ? null : `${versionRaw}`;

export default version;
