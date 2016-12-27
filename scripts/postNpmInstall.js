// Remove the webpack-dev-server grunt task since we do not use it

var fs = require('fs');
var taskFile = null;

try {
    taskFile = require.resolve('grunt-webpack/tasks/webpack-dev-server.js');
} catch (e) {}

if (taskFile) {
    console.log('Removing unused task file ' + taskFile);
    fs.unlinkSync(taskFile);
}
