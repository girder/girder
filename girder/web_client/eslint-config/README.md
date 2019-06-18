eslint-config-girder
===================

This repository contains a standalone package for
[Girder's](https://github.com/girder/girder) ESLint configuration.
It uses several ESLint plugins that must be installed at the top
level.  See the `peerDependencies` section of the `package.json`.

Install
-------

```
npm install --save-dev eslint-config-girder eslint@3.3.1 eslint-config-semistandard@6.0.2 eslint-config-standard@5.3.5 eslint-plugin-backbone@2.0.2 eslint-plugin-promise@2.0.1 eslint-plugin-standard@2.0.0 eslint-plugin-underscore@0.0.10
```

Usage
-----

In `.eslintrc`:
```json
{
  "extends": "girder"
}
```
