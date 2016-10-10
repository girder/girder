import './routes';

// Extends and overrides API
import './views/HeaderUserView';

// For testing (potentially temporary)
import * as jobs from './index';
$(function () {
    window.girder.plugins = window.girder.plugins || {};
    window.girder.plugins.jobs = jobs;
});
