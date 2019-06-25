# @girder/pug-lint-config

This npm package contains a sharable pug-lint config for use with
Girder's Backbone-based web clients and plugins.

## Usage
Typically, users of this package should depend on
`@girder/pug-lint-config` and its peerDependencies via:
```bash
npm install --save-dev @girder/pug-lint-config pug-lint@^2
```
then add `"extends": "girder"`
[to their project's local pug-lint config](https://github.com/pugjs/pug-lint#extends).
For example, within `package.json`:
```javascript
"pugLintConfig": {
    "extends": "girder"
},
```
