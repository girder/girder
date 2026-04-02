Recommended IDE Setup
---------------------

`VSCode <https://code.visualstudio.com/>`__ +
`Volar <https://marketplace.visualstudio.com/items?itemName=Vue.volar>`__
(and disable Vetur) + `TypeScript Vue Plugin
(Volar) <https://marketplace.visualstudio.com/items?itemName=Vue.vscode-typescript-vue-plugin>`__.

Type Support for ``.vue`` Imports in TS
---------------------------------------

TypeScript cannot handle type information for ``.vue`` imports by
default, so we replace the ``tsc`` CLI with ``vue-tsc`` for type
checking. In editors, we need `TypeScript Vue Plugin
(Volar) <https://marketplace.visualstudio.com/items?itemName=Vue.vscode-typescript-vue-plugin>`__
to make the TypeScript language service aware of ``.vue`` types.

If the standalone TypeScript plugin doesn’t feel fast enough to you,
Volar has also implemented a `Take Over
Mode <https://github.com/johnsoncodehk/volar/discussions/471#discussioncomment-1361669>`__
that is more performant. You can enable it by the following steps:

1. Disable the built-in TypeScript Extension

   1) Run ``Extensions: Show Built-in Extensions`` from VSCode’s command
      palette
   2) Find ``TypeScript and JavaScript Language Features``, right click
      and select ``Disable (Workspace)``

2. Reload the VSCode window by running ``Developer: Reload Window`` from
   the command palette.

Customize configuration
-----------------------

See `Vite Configuration Reference <https://vitejs.dev/config/>`__.

Project Setup
-------------

.. code:: sh

   npm install

Compile and Hot-Reload for Development
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code:: sh

   npm run dev

Type-Check, Compile and Minify for Production
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code:: sh

   npm run build

Run Unit Tests with `Vitest <https://vitest.dev/>`__
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code:: sh

   npm run test:unit

Run End-to-End Tests with `Playwright <https://playwright.dev>`__
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code:: sh

   # Install browsers for the first run
   npx playwright install

   # When testing on CI, must build the project first
   npm run build

   # Runs the end-to-end tests
   npm run test:e2e
   # Runs the tests only on Chromium
   npm run test:e2e -- --project=chromium
   # Runs the tests of a specific file
   npm run test:e2e -- tests/example.spec.ts
   # Runs the tests in debug mode
   npm run test:e2e -- --debug
