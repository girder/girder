// Remove the webpack-dev-server grunt task since we do not use it
var fs = require('fs');
var path = require('path');

var taskFile = path.join(__dirname, '..', 'node_modules', 'grunt-webpack', 'tasks', 'webpack-dev-server.js');

if (fs.existsSync(taskFile)) {
    console.log('Removing unused task file ' + taskFile);
    fs.unlinkSync(taskFile);
}
