var path = require('path');

const es2015BabelPreset = require.resolve('babel-preset-es2015');
const es2016BabelPreset = require.resolve('babel-preset-es2016');

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
                    presets: [es2015BabelPreset, es2016BabelPreset]
                }
            }
        ]
    });

    return config;
};
