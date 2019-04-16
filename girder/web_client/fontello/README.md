# @girder/fontello

This npm package contains pre-built Fontello icon files for use with
Girder's web client.

## Usage
Typically, users of this package only need to
depend on `@girder/fontello` via:
```bash
npm install --save-prod @girder/fontello
```
then import the CSS file somewhere within their Javascript sources:
```javascript
import '@girder/fontello/dist/css/fontello.css';
```
As long as Webpack or another build system is able to include the CSS
and internally referenced font files (with formats `.eot`, `.svg`,
`.ttf`, `.woff`, `.woff2`) in your final build, no additional
configuration is necessary.

If access to Fontello's animation template for elements with
`class="animate-spin"` is desired, then also add:
```javascript
import '@girder/fontello/dist/css/animation.css';
```

# Updating
To add new icons to this build, visit
[Fontello's website](http://fontello.com) and upload the
`fontello.config.json` file within this package. Select new icons
(but don't remove any), then download the new confguration via the site
and overwrite `fontello.config.json` here. Then, just run:
```bash
npm install && npm run build
```
to fetch the new icons. Finally, update the version of this package and
publish it.
