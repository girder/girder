#!/usr/bin/env node

require('colors');
var fs = require('fs');
var path = require('path');
var childProcess = require('child_process');

var pluginsDir = path.join(path.dirname(path.dirname(__dirname)), 'plugins');

fs.readdirSync(pluginsDir).forEach(function (plugin) {
    var pluginDir = path.join(pluginsDir, plugin);

    if (!fs.statSync(pluginDir).isDirectory()) {
        return;
    }

    if (fs.existsSync(path.join(pluginDir, 'package.json'))) {
        console.log('Installing npm dependencies for plugin '.bold + plugin.green);
        childProcess.execSync('npm install', {cwd: pluginDir});
    }

    // TODO also install bower deps if they exist?
});
