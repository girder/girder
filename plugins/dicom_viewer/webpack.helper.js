module.exports = function(x) {
    x.module.loaders.push({
        test: /\.glsl$/,
        include: [],
        loader: 'shader',
    });
    x.module.loaders.push({
        test: /\.json$/,
        include: [],
        loader: 'json',
    });
    return x;
}
