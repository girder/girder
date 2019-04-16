/* global process */

// Default values for external builds
const versionInfo = {
    release: null,
    gitSha: null,
    buildDate: null
};

// For Webpack to inline these variables, they must be explicitly referenced by full names
try {
    versionInfo.release = process.env.GIRDER_VERSION_RELEASE || null;
} catch (e) {}
try {
    versionInfo.gitSha = process.env.GIRDER_VERSION_GIT || null;
} catch (e) {}
try {
    versionInfo.buildDate = process.env.GIRDER_VERSION_DATE
        ? new Date(process.env.GIRDER_VERSION_DATE)
        : null;
} catch (e) {}

export default versionInfo;
