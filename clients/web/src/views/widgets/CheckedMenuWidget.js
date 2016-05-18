var CheckedActionsMenuTemplate = require('girder/templates/widgets/checkedActionsMenu.jade');
var Constants                  = require('girder/constants');
var HierarchyWidget            = require('girder/views/widgets/HierarchyWidget');
var View                       = require('girder/view');

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
            this.dropdownToggle.attr('disabled', 'disabled');
            return;
        }

        this.dropdownToggle.removeAttr('disabled');
        this.$el.html(CheckedActionsMenuTemplate({
            minFolderLevel: this.minFolderLevel,
            minItemLevel: this.minItemLevel,
            folderCount: this.folderCount,
            itemCount: this.itemCount,
            AccessType: Constants.AccessType,
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
        this.minFolderLevel = params.minFolderLevel || Constants.AccessType.READ;
        this.minItemLevel = params.minItemLevel || Constants.AccessType.READ;
        this.folderCount = params.folderCount || 0;
        this.itemCount = params.itemCount || 0;
        this.pickedCount = params.pickedCount || 0;
        this.pickedCopyAllowed = params.pickedCopyAllowed || false;
        this.pickedMoveAllowed = params.pickedMoveAllowed || false;
        this.pickedDesc = params.pickedDesc || '';
    }
});

module.exports = CheckedMenuWidget;
