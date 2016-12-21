module.exports = function(config) {
    config.module.loaders.push({
        test: /\.json$/,
        loader: 'json',
        include: ['node_modules'],
    });
    config.module.loaders.push({
        test: /\.glsl$/,
        loader: 'shader',
        include: [/node_modules(\/|\\)vtk\.js(\/|\\)/],
    });
    config.module.loaders.push({
        test: /\.js$/,
        include: [/node_modules(\/|\\)vtk\.js(\/|\\)/],
        loader: 'babel?presets[]=es2015,presets[]=react!string-replace?{"multiple":[{"search":"vtkDebugMacro","replace":"console.debug","flags":"g"},{"search":"vtkErrorMacro","replace":"console.error","flags":"g"},{"search":"vtkWarningMacro","replace":"console.warn","flags":"g"},{"search":"test.onlyIfWebGL","replace":"test","flags":"g"}]}',
    });
    return config;
}
