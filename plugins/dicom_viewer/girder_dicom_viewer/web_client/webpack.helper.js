module.exports = function (config) {
    config.module.rules.push({
        resource: {
            test: /node_modules(\/|\\)vtk\.js(\/|\\).*.glsl$/,
            include: [/node_modules(\/|\\)vtk\.js(\/|\\)/]
        },
        use: [
            require.resolve('shader-loader')
        ]
    });
    config.module.rules.push({
        resource: {
            test: /node_modules(\/|\\)vtk\.js(\/|\\).*.js$/,
            include: [/node_modules(\/|\\)vtk\.js(\/|\\)/]
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
