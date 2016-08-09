var path = require('path');
var vtkLoaders = require('../../node_modules/vtk.js/Utilities/config/webpack.loaders.js');
// var vtkLoaders = require('../../../vtk.js/Utilities/config/webpack.loaders.js');

module.exports = {
  resolve: {
    root: [
      path.resolve(__dirname, '../../node_modules'),
      path.resolve(__dirname, 'web_external'),
      path.resolve(__dirname, '../../..')
    ]
  },
  entry: path.resolve(__dirname, 'web_external/js/main.js'),
  output: {
    path: path.resolve(__dirname, '../../clients/web/static/built/plugins/dicom_viewer'),
    filename: 'plugin.min.js',
  },
  module: {
    loaders: [
      vtkLoaders,
      {
        test: /\.jade$/,
        loader: 'jade-loader',
        query: {
          doctype: 'html'
        }
      },
      {
        test: /\.styl$/,
        loaders: ['style-loader', 'css-loader', 'stylus-loader']
      },
    ],
  }
};
