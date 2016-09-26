import HierarchyWidget from 'girder/views/widgets/HierarchyWidget';
import View from 'girder/views/View';
import { AccessType } from 'girder/constants';

import CheckedActionsMenuTemplate from 'girder/templates/widgets/checkedActionsMenu.pug';

import 'girder/utilities/jquery/girderEnable';

/**
 * This widget presents a list of available batch actions
 * on a set of selected resources.
 */
var CheckedMenuWidget = View.extend({

    initialize: function (params) {
        this._fetchAndInit(params);
        this.dropdownToggle = params.dropdownToggle;
    },

    render: function () {
        // If nothing is checked, disable the parent element and return
        if (this.folderCount + this.itemCount + this.pickedCount === 0) {
            this.dropdownToggle.girderEnable(false);
            return;
        }

        this.dropdownToggle.girderEnable(true);
        this.$el.html(CheckedActionsMenuTemplate({
            minFolderLevel: this.minFolderLevel,
            minItemLevel: this.minItemLevel,
            folderCount: this.folderCount,
            itemCount: this.itemCount,
            AccessType: AccessType,
            pickedCount: this.pickedCount,
            pickedCopyAllowed: this.pickedCopyAllowed,
            pickedMoveAllowed: this.pickedMoveAllowed,
            pickedDesc: this.pickedDesc,
            HierarchyWidget: HierarchyWidget
        }));
    },

    /**
     * This should be called when the checkbox selection changes. It will
     * update and re-render the checked action menu.
     * @param minLevel The minimum access level across the checked resource set.
     * @param folderCount The number of checked folders.
     * @param itemCount The number of checked items.
     */
    update: function (params) {
        this._fetchAndInit(params);
        this.render();
    },

    _fetchAndInit: function (params) {
        this.minFolderLevel = params.minFolderLevel || AccessType.READ;
        this.minItemLevel = params.minItemLevel || AccessType.READ;
        this.folderCount = params.folderCount || 0;
        this.itemCount = params.itemCount || 0;
        this.pickedCount = params.pickedCount || 0;
        this.pickedCopyAllowed = params.pickedCopyAllowed || false;
        this.pickedMoveAllowed = params.pickedMoveAllowed || false;
        this.pickedDesc = params.pickedDesc || '';
    }
});

export default CheckedMenuWidget;
