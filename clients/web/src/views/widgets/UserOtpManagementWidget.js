import QRCode from 'qrcode';
import OTPAuth from 'url-otpauth';

import View from 'girder/views/View';

import UserOtpBeginTemplate from 'girder/templates/widgets/userOtpBegin.pug';
import UserOtpEnableTemplate from 'girder/templates/widgets/userOtpEnable.pug';
import UserOtpDisableTemplate from 'girder/templates/widgets/userOtpDisable.pug';
import 'girder/stylesheets/widgets/userOtpManagementWidget.styl';

const UserOtpManagementWidget = View.extend({
    events: {
        'click #g-user-otp-initialize-enable': function () {
            this.model.initializeEnableOtp()
                .done((totpUri) => {
                    this.totpUri = totpUri;
                    this.render();
                });
        },
        'click #g-user-otp-finalize-enable': function () {
            const otpToken = this.$('#g-user-otp-token').val().trim();

            this.model.finializeEnableOtp(otpToken)
                .done(() => {
                    // TODO: show confirmation
                    console.log('Confirm success');
                    this.totpUri = undefined;
                    this.render();
                })
                .fail((err) => {
                    // TODO: render error message
                    console.log('Finalize failed', err);
                });
        },
        'click #g-user-otp-cancel-enable': function () {
            this.totpUri = undefined;
            this.render();
        },
        'click #g-user-otp-disable': function () {
            this.model.disableOtp()
                .done(() => {
                    this.render();
                })
                .fail((err) => {
                    // TODO: render error message
                    console.log('Remove failed', err);
                });
        }
    },

    /**
     * A widget for listing and editing API keys for a user.
     *
     * @param settings.user {UserModel} The user whose keys to show.
     */
    initialize: function (settings) {
        this.model = settings.user;
    },

    render: function () {
        if (!this.model.get('otp')) {
            // OTP not set up
            if (!this.totpUri) {
                // Enablement has not started
                this._renderBegin();
            } else {
                // Enablement is pending
                this._renderConfirmation();
            }
        } else {
            // OTP already enabled
            this._renderDisable();
        }

        return this;
    },

    _renderBegin: function () {
        this.$el.html(UserOtpBeginTemplate());
    },

    _renderConfirmation: function () {
        // The OTP URI format is defined at https://github.com/google/google-authenticator/wiki/Key-Uri-Format
        const totpInfo = OTPAuth.parse(this.totpUri);

        this.$el.html(UserOtpEnableTemplate({
            totpInfo: totpInfo
        }));

        // Render the OTP as a QR code
        QRCode.toCanvas(
            this.$('#g-user-otp-qr')[0],
            this.totpUri,
            {
                errorCorrectionLevel: 'H'
            }
        );
    },

    _renderDisable: function () {
        this.$el.html(UserOtpDisableTemplate());
    }
});

export default UserOtpManagementWidget;
