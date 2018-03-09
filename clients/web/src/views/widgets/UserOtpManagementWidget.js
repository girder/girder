import QRCode from 'qrcode';
import OTPAuth from 'url-otpauth';

import View from 'girder/views/View';
import { confirm } from 'girder/dialog';
import events from 'girder/events';

import UserOtpBeginTemplate from 'girder/templates/widgets/userOtpBegin.pug';
import UserOtpConfirmationTemplate from 'girder/templates/widgets/userOtpConfirmation.pug';

const UserOtpManagementWidget = View.extend({
    events: {
        'click #g-user-otp-initialize': function () {
            this.model.initializeOtp()
                .done((otpUri) => {
                    this.otpUri = otpUri;
                    this.render();
                });
        },
        'click #g-user-otp-finalize': function () {
            const otpToken = this.$('#g-user-otp-token').value().trim();

            this.model.finializeOtp(otpToken)
                .done(() => {
                    // TODO: show confirmation
                    this.render();
                })
                .fail((err) => {
                    // TODO: render error message
                });
        },
        'click #g-user-otp-cancel': function () {
            this.otpUri = undefined;
            this.render();
        },
        'click #g-user-otp-remove': function () {
            this.model.removeOtp()
                .done(() => {
                    this.render();
                })
                .fail((err) => {
                    // TODO: render error message
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
        if (!this.model.has('otp')) {
            // OTP not set up
            if (!this.otpUri) {
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
        this.$el.html(UserOtpBeginTemplate({
        }));
    },

    _renderConfirmation: function () {
        // The OTP URI format is defined at https://github.com/google/google-authenticator/wiki/Key-Uri-Format
        const otpInfo = OTPAuth.parse(this.otpUri);

        this.$el.html(UserOtpConfirmationTemplate({
            otpInfo: otpInfo
        }));

        // Render the OTP as a QR code
        QRCode.toCanvas(
            this.$('#g-user-otp-qr')[0],
            this.otpUri,
            {
                errorCorrectionLevel: 'H',
            }
        );
    },

    _renderDisable: function () {
        // When OTP is enabled
    }
});

export default UserOtpManagementWidget;
