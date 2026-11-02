import folderActionsTemplate from './templates/folderActions.pug';
import CheckoutDialog from './views/CheckoutDialog';
import ConfigView from './views/ConfigView';

import './stylesheets/localCheckout.styl';

const $ = girder.$;
const HierarchyWidget = girder.views.widgets.HierarchyWidget;
const { wrap } = girder.utilities.PluginUtils;
const { AccessType } = girder.constants;
const router = girder.router;
const { restRequest } = girder.rest;
const { getCurrentUser } = girder.auth;
const events = girder.events;
const { exposePluginConfig } = girder.utilities.PluginUtils;

exposePluginConfig('local_checkout', 'plugins/local_checkout/config');

router.route('plugins/local_checkout/config', 'localCheckoutConfig', function () {
    events.trigger('g:navigateTo', ConfigView);
});

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
        const editEntry = this.$('.g-folder-actions-menu a.g-edit-folder').parent();
        getSettings().done((settings) => {
            const user = getCurrentUser();
            if (!settings.adminOnly || (user && user.get('admin'))) {
                editEntry.after(folderActionsTemplate());
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
