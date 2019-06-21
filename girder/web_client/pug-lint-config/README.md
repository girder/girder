# pug-lint-config-girder

This npm package contains a sharable pug-lint config for use with
Girder's Backbone-based web clients and plugins.

## Usage
Typically, users of this package should depend on
`pug-lint-config-girder` and its peerDependencies via:
```bash
npm install --save-dev pug-lint-config-girder pug-lint@^2
```
then add `"extends": "girder"`
[to their project's local pug-lint config](https://github.com/pugjs/pug-lint#extends).
For example, within `package.json`:
```javascript
"pugLintConfig": {
    "extends": "girder"
},
```
