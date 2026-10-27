#!/usr/bin/env node
// Check that a packed npm tarball is usable: every entry point that
// package.json declares is in the tarball, every "files" entry matched
// something, and the relative references inside packed CSS (url(...)) and
// JavaScript (sourceMappingURL) resolve to packed files.  Any further
// arguments are paths that must also be in the package.
//
// Usage: check_npm_package.js <package.tgz> [required-path ...]
'use strict';

const childProcess = require('child_process');
const fs = require('fs');
const os = require('os');
const path = require('path');

const METADATA_FILES = new Set(['package.json', 'readme', 'readme.md', 'readme.rst', 'readme.txt', 'license', 'license.txt', 'license.md']);

function listFiles(root) {
  const result = [];
  for (const entry of fs.readdirSync(root, {withFileTypes: true, recursive: true})) {
    if (entry.isFile()) {
      result.push(path.relative(root, path.join(entry.parentPath, entry.name)).split(path.sep).join('/'));
    }
  }
  return result.sort();
}

function normalize(ref) {
  return path.posix.normalize(ref.replace(/^\.\//, ''));
}

// Collect every path that package.json says a consumer can load.
function entryPoints(pkg) {
  const result = [];
  for (const key of ['main', 'module', 'types', 'typings', 'style']) {
    if (typeof pkg[key] === 'string') {
      result.push([key, pkg[key]]);
    }
  }
  if (typeof pkg.browser === 'string') {
    result.push(['browser', pkg.browser]);
  }
  if (typeof pkg.bin === 'string') {
    result.push(['bin', pkg.bin]);
  } else if (pkg.bin) {
    for (const [name, value] of Object.entries(pkg.bin)) {
      result.push([`bin.${name}`, value]);
    }
  }
  const walk = (value, where) => {
    if (typeof value === 'string') {
      if (!value.includes('*')) {
        result.push([where, value]);
      }
    } else if (value && typeof value === 'object') {
      for (const [key, child] of Object.entries(value)) {
        walk(child, `${where}[${JSON.stringify(key)}]`);
      }
    }
  };
  walk(pkg.exports, 'exports');
  return result;
}

function checkPackage(root, required) {
  const errors = [];
  const pkg = JSON.parse(fs.readFileSync(path.join(root, 'package.json'), 'utf8'));
  const files = listFiles(root);
  const fileSet = new Set(files);

  if (!files.some((file) => !METADATA_FILES.has(file.toLowerCase()))) {
    errors.push('the package contains no files besides package.json, README, and LICENSE');
  }

  for (const [where, ref] of entryPoints(pkg)) {
    if (!fileSet.has(normalize(ref))) {
      errors.push(`${where} refers to ${ref}, which is not in the package`);
    }
  }

  for (const ref of required) {
    if (!fileSet.has(normalize(ref))) {
      errors.push(`${ref} is required but is not in the package`);
    }
  }

  for (const entry of pkg.files || []) {
    if (/[*?[\]{}!]/.test(entry)) {
      continue;
    }
    const prefix = normalize(entry).replace(/\/$/, '');
    if (!files.some((file) => file === prefix || file.startsWith(`${prefix}/`))) {
      errors.push(`"files" lists ${entry}, but nothing in the package matches it`);
    }
  }

  for (const file of files) {
    const ext = path.extname(file);
    let refs = [];
    if (ext === '.css') {
      const text = fs.readFileSync(path.join(root, file), 'utf8');
      refs = [...text.matchAll(/url\(\s*(['"]?)([^'")]+)\1\s*\)/g)].map((match) => match[2]);
    } else if (['.js', '.cjs', '.mjs'].includes(ext)) {
      const text = fs.readFileSync(path.join(root, file), 'utf8');
      refs = [...text.matchAll(/^\/\/# sourceMappingURL=(\S+)\s*$/gm)].map((match) => match[1]);
    }
    for (const ref of refs) {
      if (/^(data:|[a-z][a-z0-9+.-]*:|\/|#)/i.test(ref)) {
        continue;
      }
      const target = path.posix.normalize(path.posix.join(path.posix.dirname(file), ref.replace(/[?#].*$/, '')));
      if (!fileSet.has(target)) {
        errors.push(`${file} refers to ${ref}, but ${target} is not in the package`);
      }
    }
  }
  return {pkg, files, errors};
}

function main() {
  const [tarball, ...required] = process.argv.slice(2);
  if (!tarball) {
    console.error('Usage: check_npm_package.js <package.tgz> [required-path ...]');
    process.exit(2);
  }
  const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'npm-package-check-'));
  try {
    childProcess.execFileSync('tar', ['-xzf', path.resolve(tarball), '-C', tmpDir]);
    const {pkg, files, errors} = checkPackage(path.join(tmpDir, 'package'), required);
    if (errors.length) {
      console.error(`${pkg.name}@${pkg.version} is not usable:`);
      for (const error of errors) {
        console.error(`  ${error}`);
      }
      process.exit(1);
    }
    console.log(`${pkg.name}@${pkg.version}: ${files.length} files, entry points and references are valid`);
  } finally {
    fs.rmSync(tmpDir, {recursive: true, force: true});
  }
}

main();
