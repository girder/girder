# @girder/eslint-config

This npm package contains a sharable ESLint config for use with Girder's
Backbone-based web clients and plugins.

## Usage
Typically, users of this package should depend on
`@girder/eslint-config` and its peerDependencies via:
```bash
npm install --save-dev @girder/eslint-config eslint@^5 eslint-config-semistandard@^13 eslint-config-standard@^12 eslint-plugin-backbone eslint-plugin-import eslint-plugin-node eslint-plugin-promise eslint-plugin-standard eslint-plugin-underscore
```
then add `"extends": "@girder"`
[to their project's local ESLint config](https://eslint.org/docs/developer-guide/shareable-configs#using-a-shareable-config).
For example, within `package.json`:
```javascript
"eslintConfig": {
    "extends": "@girder"
}
```
