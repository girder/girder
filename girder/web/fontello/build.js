#!/usr/bin/env node
// Build the Fontello icon font from fontello.config.json without using the
// fontello.com web service.  Glyph outlines and CSS templates come from a
// pinned commit of the Fontello project (https://github.com/fontello/fontello),
// and the font conversion mirrors its font builder
// (internal/fontello/font_build/_lib/{config,worker}.js).
'use strict';

const childProcess = require('child_process');
const crypto = require('crypto');
const fs = require('fs');
const os = require('os');
const path = require('path');

const ejs = require('ejs');
const svg2ttf = require('svg2ttf');
const svgpath = require('svgpath');
const ttf2eot = require('ttf2eot');
const ttf2woff = require('ttf2woff');
const wawoff2 = require('wawoff2');

const FONTELLO_COMMIT = '71330f51d11b00fa75b6c516db2ea4d62da67330';
const FONTELLO_FILES = {
  'lib/embedded_fonts/server_config.js': '8e4c488262ff52220e1f53e09a9b99e5ad724cf2979595aae6bc3ddb62913c6b',
  'support/font-templates/css/css.ejs': 'b4a091ca48ae8f88019bd85770978ccd07ee0c2f9cc9e83959b1227e8390c475',
  'support/font-templates/css/animation.css': 'c5221cfe37e6f0b011346164e7b3378c106807dc0d42fc0887440ab36c09e205',
  'support/font-templates/font/svg.ejs': '5b5bfb684cb12d1333c2c69347181099ef75ba131400d44092d2c234b14a3b6c'
};
const CACHE_DIR = path.join(__dirname, 'node_modules', '.cache', 'fontello', FONTELLO_COMMIT);
const CONFIG_PATH = path.join(__dirname, 'fontello.config.json');
const DIST_DIR = path.join(__dirname, 'dist');

function sha256(data) {
  return crypto.createHash('sha256').update(data).digest('hex');
}

// Return the contents of a file from the pinned Fontello commit, downloading
// and verifying it on first use.
async function fontelloSource(relPath) {
  const cachePath = path.join(CACHE_DIR, relPath);
  const expected = FONTELLO_FILES[relPath];
  if (fs.existsSync(cachePath)) {
    const cached = fs.readFileSync(cachePath);
    if (sha256(cached) === expected) {
      return cached.toString('utf8');
    }
  }
  const url = `https://raw.githubusercontent.com/fontello/fontello/${FONTELLO_COMMIT}/${relPath}`;
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`Failed to download ${url}: HTTP ${response.status}`);
  }
  const data = Buffer.from(await response.arrayBuffer());
  if (sha256(data) !== expected) {
    throw new Error(`Checksum mismatch for ${url}`);
  }
  fs.mkdirSync(path.dirname(cachePath), {recursive: true});
  fs.writeFileSync(cachePath, data);
  return data.toString('utf8');
}

// server_config.js is a "module.exports = {...};" wrapper around JSON; parse
// it as data rather than executing downloaded code.
function parseEmbeddedFonts(source) {
  return JSON.parse(source.replace(/^\s*module\.exports\s*=\s*/, '').replace(/;\s*$/, ''));
}

function outlinePath(d, scale, ascent) {
  return svgpath(d).scale(scale, -scale).translate(0, ascent).abs().round(0).rel();
}

// Convert the client config (fontello.config.json) to the builder config used
// by the Fontello templates.
function builderConfig(clientConfig, embedded) {
  const unitsPerEm = +clientConfig.units_per_em || 1000;
  const ascent = +clientConfig.ascent || 850;
  const scale = unitsPerEm / 1000;
  const glyphs = [];
  let usesEmbedded = false;

  for (const glyph of clientConfig.glyphs) {
    if (glyph.src === 'custom_icons') {
      if (!glyph.selected) {
        continue;
      }
      const outline = outlinePath(glyph.svg.path, scale, ascent);
      glyphs.push({
        src: glyph.src,
        uid: glyph.uid,
        code: glyph.code,
        css: glyph.css,
        width: +(glyph.svg.width * scale).toFixed(1),
        d: outline.toString(),
        segments: outline.segments.length
      });
      continue;
    }
    const source = embedded.uids[glyph.uid];
    if (!source) {
      throw new Error(`Unknown glyph ${glyph.uid} (${glyph.css}) from ${glyph.src}`);
    }
    usesEmbedded = true;
    const outline = outlinePath(source.svg.d, scale, ascent);
    glyphs.push({
      src: source.fontname,
      uid: glyph.uid,
      code: glyph.code || source.code,
      css: glyph.css || source.css,
      'css-ext': source['css-ext'],
      width: +(source.svg.width * scale).toFixed(1),
      d: outline.toString(),
      segments: outline.segments.length
    });
  }
  if (!glyphs.length) {
    throw new Error('No glyphs selected in fontello.config.json');
  }
  glyphs.sort((a, b) => a.code - b.code);

  const fontname = clientConfig.name ? String(clientConfig.name).replace(/[^a-z0-9\-_]+/g, '-') : 'fontello';
  const defaultCopyright = `Copyright (C) ${new Date().getFullYear()} by original authors @ fontello.com`;
  return {
    font: {
      fontname,
      fullname: fontname,
      familyname: fontname,
      copyright: usesEmbedded ? defaultCopyright : (clientConfig.copyright || defaultCopyright),
      ascent,
      descent: ascent - unitsPerEm,
      weight: 400
    },
    hinting: clientConfig.hinting !== false,
    meta: {
      columns: 4,
      css_prefix_text: clientConfig.css_prefix_text || 'icon-',
      css_use_suffix: Boolean(clientConfig.css_use_suffix)
    },
    glyphs
  };
}

// Autohint with ttfautohint (as fontello.com does) when it is installed.
function autohint(ttf, config) {
  if (!config.hinting) {
    return ttf;
  }
  if (Math.max(...config.glyphs.map((glyph) => glyph.segments)) > 500) {
    console.warn('Skipping hinting: font has glyphs with more than 500 segments');
    return ttf;
  }
  const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'fontello-'));
  try {
    const unhinted = path.join(tmpDir, 'unhinted.ttf');
    const hinted = path.join(tmpDir, 'hinted.ttf');
    fs.writeFileSync(unhinted, ttf);
    childProcess.execFileSync('ttfautohint', ['--no-info', '--symbol', '--fallback-script=latn', unhinted, hinted]);
    return new Uint8Array(fs.readFileSync(hinted));
  } catch (err) {
    if (err.code === 'ENOENT' && err.path === 'ttfautohint') {
      console.warn('ttfautohint not found; building an unhinted font');
      return ttf;
    }
    throw err;
  } finally {
    fs.rmSync(tmpDir, {recursive: true, force: true});
  }
}

async function main() {
  const clientConfig = JSON.parse(fs.readFileSync(CONFIG_PATH, 'utf8'));
  const embedded = parseEmbeddedFonts(await fontelloSource('lib/embedded_fonts/server_config.js'));
  const config = builderConfig(clientConfig, embedded);
  const fontname = config.font.fontname;

  const svgFont = ejs.render(await fontelloSource('support/font-templates/font/svg.ejs'), config);
  const ttf = autohint(new Uint8Array(svg2ttf(svgFont, {copyright: config.font.copyright}).buffer), config);
  const css = ejs.render(await fontelloSource('support/font-templates/css/css.ejs'), config)
    .replace(/\.\.\/font\//g, '../fonts/');
  const animationCss = await fontelloSource('support/font-templates/css/animation.css');

  fs.rmSync(DIST_DIR, {recursive: true, force: true});
  const fontsDir = path.join(DIST_DIR, 'fonts');
  const cssDir = path.join(DIST_DIR, 'css');
  fs.mkdirSync(fontsDir, {recursive: true});
  fs.mkdirSync(cssDir, {recursive: true});
  fs.writeFileSync(path.join(fontsDir, `${fontname}.svg`), svgFont);
  fs.writeFileSync(path.join(fontsDir, `${fontname}.ttf`), ttf);
  fs.writeFileSync(path.join(fontsDir, `${fontname}.eot`), ttf2eot(ttf));
  fs.writeFileSync(path.join(fontsDir, `${fontname}.woff`), ttf2woff(ttf));
  fs.writeFileSync(path.join(fontsDir, `${fontname}.woff2`), await wawoff2.compress(ttf));
  fs.writeFileSync(path.join(cssDir, `${fontname}.css`), css);
  fs.writeFileSync(path.join(cssDir, 'animation.css'), animationCss);
  console.log(`Built ${config.glyphs.length} glyphs into ${path.relative(process.cwd(), DIST_DIR) || '.'}`);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
