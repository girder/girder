/**
 * Copyright 2015 Kitware Inc.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *    http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

var webpack = require('webpack');

var LoaderOptionsPlugin = webpack.LoaderOptionsPlugin;

module.exports = {
    debug: true,
    devtool: 'source-map',
    cache: true,
    plugins: [
        // https://github.com/webpack/webpack/issues/283
        // https://github.com/webpack/webpack/issues/2061#issuecomment-228932941
        // https://gist.github.com/sokra/27b24881210b56bbaff7#loader-options--minimize
        // but unclear and confusing as to how far it has been implemented
        new LoaderOptionsPlugin({
            minimize: false,
            debug: true
        })
    ]
};
