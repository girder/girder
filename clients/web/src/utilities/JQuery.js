/**
 * Define jQuery plugins within this scope.
 */
(function ($) {

    /**
     * This should be used instead of calling bootstrap's modal() jQuery
     * method directly. This unbinds all previous events from the dialog,
     * then calls modal on it and binds the bootstrap close events.
     * @param view The view object. Pass "false" for special cases where the
     *             dialog does not correspond to a View object.
     */
    $.fn.girderModal = function (view) {
        var that = this;
        this.off().modal().find('[data-dismiss="modal"]')
            .unbind('click').click(function () {
                that.modal('hide');
            });
        if (view !== false) {
            view.delegateEvents();
        }
        return this;
    };
}(jQuery));
