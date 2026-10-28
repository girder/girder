import template from '../templates/checkoutDialog.pug';

const View = girder.views.View;
const events = girder.events;
const { restRequest } = girder.rest;
const { getCurrentUser } = girder.auth;
const { formatDate, formatSize, DATE_MINUTE } = girder.misc;

/**
 * A dialog that shows how much of a folder is local and lets the user
 * check the folder out, change the duration, or release it.
 */
const CheckoutDialog = View.extend({
    events: {
        'submit #g-local-checkout-form': function (e) {
            e.preventDefault();
            const days = parseInt(this.$('#g-local-checkout-days').val(), 10);
            if (!(days >= 1)) {
                this.$('.g-validation-failed-message').text('Enter a number of days.');
                return;
            }
            this._save({ days }, this.status.checkout
                ? 'The checkout duration was updated; any files that are not yet local are being copied.'
                : 'Copying files to local storage has started.');
        },
        'click .g-local-checkout-release': function () {
            this._save({ days: 0 }, 'The checkout was released; local copies are being removed.');
        }
    },

    initialize: function (settings) {
        this.folder = settings.folder;
        this.status = null;
    },

    render: function () {
        const checkout = this.status && this.status.checkout;
        let remainingDays = 0;
        let defaultDays = 0;
        if (checkout) {
            const msRemaining = new Date(checkout.expires) - Date.now();
            remainingDays = Math.max(0, Math.ceil(msRemaining / (24 * 3600 * 1000)));
            defaultDays = Math.max(1, remainingDays);
        } else if (this.status) {
            defaultDays = Math.min(30, this.status.maxDays);
        }
        this.$el.html(template({
            folder: this.folder,
            status: this.status,
            remainingDays,
            defaultDays,
            isAdmin: !!(getCurrentUser() && getCurrentUser().get('admin')),
            formatDate,
            formatSize,
            DATE_MINUTE
        })).girderModal(this);

        if (!this.status) {
            restRequest({
                url: `folder/${this.folder.id}/local_checkout`,
                method: 'GET'
            }).done((resp) => {
                this.status = resp;
                this.render();
            }).fail((resp) => {
                this.$('.g-validation-failed-message').text(resp.responseJSON.message);
            });
        }
        return this;
    },

    _save: function (data, message) {
        this.$('.g-validation-failed-message').empty();
        this.$('.modal-footer button').girderEnable(false);
        restRequest({
            url: `folder/${this.folder.id}/local_checkout`,
            method: 'PUT',
            data,
            error: null
        }).done(() => {
            this.$el.modal('hide');
            events.trigger('g:alert', {
                icon: 'location',
                text: message,
                type: 'success',
                timeout: 5000
            });
        }).fail((resp) => {
            this.$('.modal-footer button').girderEnable(true);
            this.$('.g-validation-failed-message').text(resp.responseJSON.message);
        });
    }
});

export default CheckoutDialog;
