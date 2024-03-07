# Girder + Vite Proof of Concept

This is a proof of concept of a Vite SPA build for Girder.

## Basic Setup
* Get girder server running on localhost:8080 (i.e. clone this repo, `pip install -e .`, `girder serve`)
* You need to enable a CORS allowed origin in Girder settings for the experimental SPA. This is somewhat a chicken-and-egg scenario since it's easiest to change this setting from the Girder web admin UI itself. This could be accomplished by having a separate checkout of `girder` on the `master` branch where you do `girder build` (`girder build` is broken on this branch).
* `cd girder/web/core`
* `npm i`
* `npm run build`
* `cd girder/web/client`
* To avoid building plugins, delete plugin package dependencies in `package.json`.
* `npm i`
* `npm run dev`
* Unit test: `npm run test:unit`
* End-to-end test: `npm run test:e2e`

## What Works
* Girder core interface
* Homepage plugin
* Jobs plugin (maybe?)
* Some really basic JS unit testing with vitest and JS end-to-end testing with playwright

## What Doesn't Work
* Much of the large volume of existing end-to-end tests
* Much of the plugin client code

## Plugin Conversion

Notes from converting the `jobs` plugin:

* Convert imports
  * Open the global find/replace left side panel in VSCode.
  * Find `import (.*) from '@girder\/core\/(.*)';` with regex mode selected (`.*` button).
  * Replace with `const $1 = girder.$2;`.
  * Select the book icon under "files to include" to only replace in open editor windows.
  * For each `.js` file in the plugin, open it and do the following:
    * Perform "Replace all" in the open file.
    * Perform a find/replace in the file (normal `Cmd/Ctrl-F`) with the changed lines selected and replace `/` with `.`. To replace all within a selection use the "3-text-lines" button in the find/replace overlay.
    * Move the new `const` lines under any remaining `import` lines.
    * Replace any of the following lines: `import _ from 'underscore';`,
      `import $ from 'query';`,
      `import moment from 'moment';` with `const { _, $, moment } = girder;` to utilize Girder core's versions of those libraries.
* Update `package.json`
  * Copy `vite-env.d.ts` and `vite.config.ts` from `plugins/homepage/girder_homepage/web_client` to your plugin's web directory.
  * Replace everything under the `"repository"` config in your plugin's `package.json` with everything under the `"repository"` config in `plugins/homepage/girder_homepage/web_client/package.json`.
  * Rename things in `package.json` and `vite.config.ts` according to the plugin npm package name, which should now contain `girder-plugin` so it is discovered and initialized properly when bundled into a client.
* Manual testing:
  * Run `npm run build` for the plugin.
  * Add a line to `girder/web/client/package.json` to add a `file:` dependency to the plugin.
  * Ensure `girder serve` is running on the default port on your system with CORS (see Basic Setup).
  * Run `npm run dev` in `girder/web/client` and visit the URL serving the client.
* Automated testing: TODO (no official process for migrating tests yet).
