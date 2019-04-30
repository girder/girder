var path = require('path');

module.exports = {
    node_modules: path.resolve('node_modules'),
    plugins: path.resolve(__dirname, 'plugins'),
    static: path.resolve('static')
};
