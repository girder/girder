/**
 * This widget presents a list of available batch actions
 * on a set of selected resources.
 */
girder.views.CheckedMenuWidget = girder.View.extend({

    initialize: function (params) {
        this.folderCount = params.folderCount || 0;
        this.itemCount = params.itemCount || 0;
        this.minFolderLevel = girder.AccessType.READ;
        this.minItemLevel = girder.AccessType.READ;

        this.dropdownToggle = params.dropdownToggle;
    },

    render: function () {
        // If nothing is checked, disable the parent element and return
        if (this.folderCount + this.itemCount === 0) {
            this.dropdownToggle.attr('disabled', 'disabled');
            return;
        }

        this.dropdownToggle.removeAttr('disabled');
        this.$el.html(jade.templates.checkedActionsMenu({
            minFolderLevel: this.minFolderLevel,
            minItemLevel: this.minItemLevel,
            folderCount: this.folderCount,
            itemCount: this.itemCount,
            AccessType: girder.AccessType
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
        this.minFolderLevel = params.minFolderLevel;
        this.minItemLevel = params.minItemLevel;
        this.folderCount = params.folderCount || 0;
        this.itemCount = params.itemCount || 0;

        this.render();
    }
});
