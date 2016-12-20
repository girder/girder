var vtkLoaders = require('../../node_modules/vtk.js/Utilities/config/webpack.loaders.js');

module.exports = function(x) {
    for (var i = 0; i < vtkLoaders.length; i++) {
        vtkLoaders[i].include = ['node_modules'];
        x.module.loaders.push(vtkLoaders[i]);
    }
    return x;
}
