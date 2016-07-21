import { AccessType } from 'girder/constants';
import { getCurrentUser } from 'girder/auth';
import { wrap } from 'girder/utilities/PluginUtils';

import QuotaPoliciesWidget from './QuotaPoliciesWidget';

function extendView(View, Template, modelType) {
    var eventSelector = 'click .g-' + modelType + '-policies';
    View.prototype.events[eventSelector] = 'editPolicies';

    var _initialize = View.prototype.initialize;
    View.prototype.initialize = function (settings) {
        this.quota = ((settings || {}).dialog === 'quota');
        _initialize.apply(this, arguments);
    };

    wrap(View, 'render', function (render) {
        var el, settings;
        /* Add the quota menu item to the resource menu as needed */
        render.call(this);
        el = $('.g-' + modelType + '-header a.g-delete-' + modelType).closest('li');
        settings = {
            AccessType: AccessType,
            currentUser: getCurrentUser()
        };
        settings[modelType] = this.model;
        el.before(Template(settings));
        if (this.quota) {
            this.quota = null;
            this.editPolicies();
        }
    });

    View.prototype.editPolicies = function () {
        new QuotaPoliciesWidget({
            el: $('#g-dialog-container'),
            model: this.model,
            modelType: modelType,
            parentView: this
        }).on('g:saved', function () {
            this.render();
        }, this);
    };
}

export default extendView;
