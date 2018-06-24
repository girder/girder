module.exports = function (config) {
    config.module.rules.push({
        resource: {
            test: /node_modules(\/|\\)candela(\/|\\).*.js$/,
            include: [/node_modules(\/|\\)candela(\/|\\)/]
        },
        use: [
            {
                loader: 'babel-loader',
                options: {
                    presets: ['env']
                }
            }
        ]
    });
    return config;
};
