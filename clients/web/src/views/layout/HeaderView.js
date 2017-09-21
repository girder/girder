import _ from 'underscore';

import LayoutHeaderUserView from 'girder/views/layout/HeaderUserView';
import router from 'girder/router';
import SearchFieldWidget from 'girder/views/widgets/SearchFieldWidget';
import View from 'girder/views/View';

import LayoutHeaderTemplate from 'girder/templates/layout/layoutHeader.pug';

import 'girder/stylesheets/layout/header.styl';

/**
 * This view shows the header in the layout.
 */
var LayoutHeaderView = View.extend({
    events: {
        'click .g-app-title': function () {
            router.navigate('', {trigger: true});
        }
    },

    initialize: function (settings) {
        this.brandName = settings.brandName || 'Girder';
        this.bannerColor = settings.bannerColor || '#3F3B3B';
        this.userView = new LayoutHeaderUserView({
            parentView: this
        });

        this.searchWidget = new SearchFieldWidget({
            placeholder: 'Quick search...',
            types: ['item', 'folder', 'group', 'collection', 'user'],
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
        const red = parseInt(bannerColor.substr(1, 2), 16);
        const green = parseInt(bannerColor.substr(3, 2), 16);
        const blue = parseInt(bannerColor.substr(5, 2), 16);
        const colorArray = _.map([red, green, blue], (component) => {
            component = component / 255.0;
            if (component <= 0.03928) {
                component = component / 12.92;
            } else {
                component = Math.pow((component + 0.055) / 1.055, 2.4);
            }
            return component;
        });
        const L = 0.2126 * colorArray[0] + 0.7152 * colorArray[1] + 0.0722 * colorArray[2];
        return ((L + 0.05) / (0.0 + 0.05) > (1.0 + 0.05) / (L + 0.05)) ? '#000000' : '#ffffff';
    }
});

export default LayoutHeaderView;
