import folderActionsTemplate from './templates/folderActions.pug';
import CheckoutDialog from './views/CheckoutDialog';
import ConfigView from './views/ConfigView';

import './stylesheets/localCheckout.styl';

const $ = girder.$;
const HierarchyWidget = girder.views.widgets.HierarchyWidget;
const { wrap } = girder.utilities.PluginUtils;
const { AccessType } = girder.constants;
const router = girder.router;
const events = girder.events;
const { exposePluginConfig } = girder.utilities.PluginUtils;

exposePluginConfig('local_checkout', 'plugins/local_checkout/config');

router.route('plugins/local_checkout/config', 'localCheckoutConfig', function () {
    events.trigger('g:navigateTo', ConfigView);
});

// Add an entry to the folder actions menu for users who can write to the folder
wrap(HierarchyWidget, 'render', function (render) {
    render.call(this);

    if (this.parentModel.resourceName === 'folder' &&
            this.parentModel.getAccessLevel() >= AccessType.WRITE) {
        this.$('.g-folder-actions-menu a.g-edit-folder').parent().after(folderActionsTemplate());
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
