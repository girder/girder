# Girder + Vite Proof of Concept

This is a proof of concept of a Vite SPA build for Girder.

How to use it:
* Get girder server running on localhost:8080 (i.e. clone this repo, `pip install -e .`, `girder serve`)
* You need to enable a CORS allowed origin in Girder settings for the experimental SPA. This is somewhat a chicken-and-egg scenario since it's easiest to change this setting from the Girder web admin UI itself. This could be accomplished by having a separate checkout of `girder` on the `master` branch where you do `girder build` (`girder build` is broken on this branch).
* `cd girder/web_client`
* `npm i`
* `npm run dev`

What works
* Girder core interface

What doesn't work
* The Girder logo does not work due to Pug `require()` being broken
* Any plugin client code
* Any client testing

# Vue 3 + TypeScript + Vite

This template should help get you started developing with Vue 3 and TypeScript in Vite. The template uses Vue 3 `<script setup>` SFCs, check out the [script setup docs](https://v3.vuejs.org/api/sfc-script-setup.html#sfc-script-setup) to learn more.

## Recommended IDE Setup

- [VS Code](https://code.visualstudio.com/) + [Volar](https://marketplace.visualstudio.com/items?itemName=Vue.volar) (and disable Vetur) + [TypeScript Vue Plugin (Volar)](https://marketplace.visualstudio.com/items?itemName=Vue.vscode-typescript-vue-plugin).

## Type Support For `.vue` Imports in TS

TypeScript cannot handle type information for `.vue` imports by default, so we replace the `tsc` CLI with `vue-tsc` for type checking. In editors, we need [TypeScript Vue Plugin (Volar)](https://marketplace.visualstudio.com/items?itemName=Vue.vscode-typescript-vue-plugin) to make the TypeScript language service aware of `.vue` types.

If the standalone TypeScript plugin doesn't feel fast enough to you, Volar has also implemented a [Take Over Mode](https://github.com/johnsoncodehk/volar/discussions/471#discussioncomment-1361669) that is more performant. You can enable it by the following steps:

1. Disable the built-in TypeScript Extension
   1. Run `Extensions: Show Built-in Extensions` from VSCode's command palette
   2. Find `TypeScript and JavaScript Language Features`, right click and select `Disable (Workspace)`
2. Reload the VSCode window by running `Developer: Reload Window` from the command palette.
