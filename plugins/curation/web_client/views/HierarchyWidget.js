import $ from 'jquery';
import _ from 'underscore';

import HierarchyWidget from 'girder/views/widgets/HierarchyWidget';
import { getCurrentUser } from 'girder/auth';
import { restRequest } from 'girder/rest';
import { wrap } from 'girder/utilities/PluginUtils';

import HierarchyWidgetCurationButtonTemplate from '../templates/hierarchyWidgetCurationButton.pug';

import CurationDialog from './CurationDialog';

function _addCurationButton() {
    $('.g-folder-actions-menu').append(HierarchyWidgetCurationButtonTemplate());
}

// add curation button to hierarchy widget
wrap(HierarchyWidget, 'render', function (render) {
    render.call(this);

    if (this.parentModel.get('_modelType') === 'folder') {
        // add button if an admin or if curation is enabled
        if (getCurrentUser().get('admin')) {
            _addCurationButton();
        } else {
            restRequest({
                url: 'folder/' + this.parentModel.get('_id') + '/curation'
            }).done(_.bind(function (resp) {
                if (resp.enabled) {
                    _addCurationButton();
                }
            }, this));
        }
    }

    return this;
});

// launch modal when curation button is clicked
HierarchyWidget.prototype.events['click .g-curation-button'] = function (e) {
    /* eslint-disable no-new */
    new CurationDialog({
        el: $('#g-dialog-container'),
        parentView: this,
        folder: this.parentModel
    });
    /* eslint-enable no-new */
};
