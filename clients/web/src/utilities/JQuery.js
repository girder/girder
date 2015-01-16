/**
 * Define jQuery plugins within this scope.
 */
(function ($) {

    /**
     * This should be used instead of calling bootstrap's modal() jQuery
     * method directly. This unbinds all previous events from the dialog,
     * then calls modal on it and binds the bootstrap close events.
     * @param view The view object. Pass "false" for special cases where the
     *             dialog does not correspond to a View object.  Pass 'close'
     *             to just close an open modal dialog.
     */
    $.fn.girderModal = function (view) {
        var that = this;
        /* If we have a modal dialog open, or one is in the process of closing,
         * close that dialog before opening the new one.  This prevents
         * layering modal dialogs, but also makes sure that we don't have a
         * problem switching from one modal dialog to another. */
        if ($(this).is('.modal')) {
            /* We have to reach into the backbone modal object a little to see
             * if we need to do anything. */
            if ($(this).data('bs.modal') && $(this).data('bs.modal').isShown) {
                $(this).modal('hide');
            }
            $(this).modal('removeBackdrop');
        }
        if (view !== 'close') {
            this.off().modal().find('[data-dismiss="modal"]')
                .unbind('click').click(function () {
                    that.modal('hide');
                });
            if (view !== false) {
                view.delegateEvents();
            }
        }
        return this;
    };
}(jQuery));
