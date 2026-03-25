const versionRaw = import.meta.env.GIRDER_VERSION || null;

// Enforce that it's a string or null to make TypeScript happy
const version = versionRaw === null ? null : `${versionRaw}`;

export default version;
