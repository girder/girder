var path = require('path');

module.exports = function (config, data) {
    var candelaDir = path.resolve(data.nodeDir, 'candela');

    config.module.rules.push({
        resource: {
            test: new RegExp(candelaDir + '.*.js$'),
            include: [candelaDir]
        },
        use: [
            {
                loader: 'babel-loader',
                options: {
                    presets: ['es2015', 'es2016']
                }
            }
        ]
    });

    return config;
};
