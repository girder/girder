import './routes';

import $ from 'jquery';

import HierarchyWidget from '@girder/core/views/widgets/HierarchyWidget';
import events from '@girder/core/events';
import { AccessType } from '@girder/core/constants';
import { getCurrentUser } from '@girder/core/auth';
import { restRequest } from '@girder/core/rest';
import { wrap } from '@girder/core/utilities/PluginUtils';

import folderActionsTemplate from './templates/folderActions.pug';
import CheckoutDialog from './views/CheckoutDialog';

import './stylesheets/localCheckout.styl';

let settingsPromise = null;

/**
 * Fetch the plugin settings once per session; they only change through the
 * admin config page.
 */
function getSettings() {
    if (!settingsPromise) {
        settingsPromise = restRequest({ url: 'local_checkout/settings', method: 'GET' });
    }
    return settingsPromise;
}

// Saving the config page may change who sees the menu item
events.on('g:localCheckout.settingsChanged', () => {
    settingsPromise = null;
});

// Add an entry to the folder actions menu for users who can write to the
// folder, unless checkouts are restricted to administrators and the user is
// not one
wrap(HierarchyWidget, 'render', function (render) {
    render.call(this);

    if (this.parentModel.resourceName === 'folder' &&
            this.parentModel.getAccessLevel() >= AccessType.WRITE) {
        const editFolder = this.$('.g-folder-actions-menu a.g-edit-folder');
        // The classic menu wraps each link in a list item; the htk menu holds
        // its links directly
        const legacyMenu = editFolder.parent().is('li');
        const editEntry = legacyMenu ? editFolder.parent() : editFolder;
        getSettings().done((settings) => {
            const user = getCurrentUser();
            if (!settings.adminOnly || (user && user.get('admin'))) {
                editEntry.after(folderActionsTemplate({ legacyMenu }));
            }
        });
    }
    return this;
});

HierarchyWidget.prototype.events['click a.g-local-checkout'] = function () {
    new CheckoutDialog({
        el: $('#g-dialog-container'),
        folder: this.parentModel,
        parentView: this
    }).render();
};
