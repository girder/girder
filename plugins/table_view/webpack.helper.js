module.exports = function (config) {
    config.module.rules.push({
        resource: {
            test: /\.js$/,
            include: [/node_modules\/vega-.*/]
        },
        use: [{
            loader: 'babel-loader',
            options: {
                presets: ['env']
            }
        }]
    });
    return config;
};
