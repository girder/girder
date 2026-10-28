@girder/fontello
================

This npm package contains pre-built Fontello icon files for use with
Girder’s web client.

Usage
-----

Typically, users of this package only need to depend on
``@girder/fontello`` via:

.. code:: bash

   npm install --save-prod @girder/fontello

then import the CSS file somewhere within their Javascript sources:

.. code:: javascript

   import '@girder/fontello/dist/css/fontello.css';

As long as Webpack or another build system is able to include the CSS
and internally referenced font files (with formats ``.eot``, ``.svg``,
``.ttf``, ``.woff``, ``.woff2``) in your final build, no additional
configuration is necessary.

If access to Fontello’s animation template for elements with
``class="animate-spin"`` is desired, then also add:

.. code:: javascript

   import '@girder/fontello/dist/css/animation.css';

Updating
========

To add new icons to this build, visit `Fontello’s
website <https://fontello.com>`__ and import the
``fontello.config.json`` file within this package. Select new icons (but
don’t remove any), then download the new configuration via the site and
overwrite ``fontello.config.json`` here. Then, just run:

.. code:: bash

   npm install && npm run build

``build.js`` builds the font locally; it does not use the fontello.com
service. It uses the glyph data and CSS templates from a pinned commit of
the `Fontello project <https://github.com/fontello/fontello>`__, downloaded
from GitHub and checksum-verified on first use. If ``ttfautohint`` is
installed (for example, ``apt-get install ttfautohint``), the font is
hinted, as fontello.com does; otherwise an unhinted font is built and a
warning is printed. Icons that are newer than the pinned commit require
updating ``FONTELLO_COMMIT`` and the checksums in ``build.js``.
