module.exports = function (config) {
    config.module.rules.push({
        resource: {
            test: /\.glsl$/,
            include: [/node_modules(\/|\\)vtk\.js(\/|\\)/]
        },
        use: [
            'shader-loader'
        ]
    });
    config.module.rules.push({
        resource: {
            test: /\.js$/,
            include: [/node_modules(\/|\\)vtk\.js(\/|\\)/]
        },
        use: [
            {
                loader: 'babel-loader',
                options: {
                    presets: ['es2015']
                }
            }
        ]
    });
    return config;
};
