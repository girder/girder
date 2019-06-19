import _ from 'underscore';

import LayoutHeaderUserView from '@girder/core/views/layout/HeaderUserView';
import router from '@girder/core/router';
import SearchFieldWidget from '@girder/core/views/widgets/SearchFieldWidget';
import View from '@girder/core/views/View';

import LayoutHeaderTemplate from '@girder/core/templates/layout/layoutHeader.pug';

import '@girder/core/stylesheets/layout/header.styl';

/**
 * This view shows the header in the layout.
 */
var LayoutHeaderView = View.extend({
    events: {
        'click .g-app-title': function () {
            router.navigate('', { trigger: true });
        }
    },

    initialize: function (settings) {
        this.brandName = settings.brandName || 'Girder';
        this.bannerColor = settings.bannerColor || '#3F3B3B';

        this.userView = new LayoutHeaderUserView({
            parentView: this,
            registrationPolicy: settings.registrationPolicy
        });

        /*
         * The order of types correspond to the order of the displayed types results on the dialog box.
         */
        this.searchWidget = new SearchFieldWidget({
            placeholder: 'Quick search...',
            types: ['collection', 'folder', 'item', 'group', 'user'],
            parentView: this
        }).on('g:resultClicked', function (result) {
            this.searchWidget.resetState();
            router.navigate(result.type + '/' + result.id, {
                trigger: true
            });
        }, this);
    },

    render: function () {
        var textColor = this._getTextColor(this.bannerColor);
        this.$el.html(LayoutHeaderTemplate({
            brandName: this.brandName,
            bannerColor: this.bannerColor,
            textColor: textColor
        }));
        this.userView.setElement(this.$('.g-current-user-wrapper')).render();
        if (textColor !== '#ffffff') {
            // We will lose the hover color by setting this, so only do that if necessary
            this.userView.$('.g-user-text a').css('color', textColor);
        }
        this.searchWidget.setElement(this.$('.g-quick-search-container')).render();

        return this;
    },

    _getTextColor: function (bannerColor) {
        // https://stackoverflow.com/a/3943023
        const hexRed = bannerColor.substr(1, 2);
        const hexGreen = bannerColor.substr(3, 2);
        const hexBlue = bannerColor.substr(5, 2);
        const sRGB = _.map([hexRed, hexGreen, hexBlue], (hexComponent) =>
            parseInt(hexComponent, 16) / 255.0
        );
        const linearRBG = _.map(sRGB, (component) =>
            (component <= 0.03928)
                ? component / 12.92
                : Math.pow((component + 0.055) / 1.055, 2.4)
        );
        const L = 0.2126 * linearRBG[0] + 0.7152 * linearRBG[1] + 0.0722 * linearRBG[2];
        return ((L + 0.05) / (0.0 + 0.05) > (1.0 + 0.05) / (L + 0.05))
            ? '#000000'
            : '#ffffff';
    }
});

export default LayoutHeaderView;
