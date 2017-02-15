module.exports = function (config) {
    config.module.loaders.push({
        test: /\.glsl$/,
        loader: 'shader-loader',
        include: [/node_modules(\/|\\)vtk\.js(\/|\\)/],
    });
    config.module.loaders.push({
        test: /\.js$/,
        include: [/node_modules(\/|\\)vtk\.js(\/|\\)/],
        loaders: [{
            loader: 'babel-loader',
            query: {
                presets: ['es2015', 'react']
            }
        }, {
            loader: 'string-replace-loader',
            query: {
                multiple: [
                    {search: /vtkDebugMacro/g, replace: 'console.debug'},
                    {search: /vtkErrorMacro/g, replace: 'console.error'},
                    {search: /vtkWarningMacro/g, replace: 'console.warn'},
                    {search: /test\.onlyIfWebGL/g, replace: 'test'}
                ]
            }
        }]
    });
    return config;
};
