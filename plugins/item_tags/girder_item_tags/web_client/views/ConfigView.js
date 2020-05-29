import { AccessType } from '@girder/core/constants';
import PluginConfigBreadcrumbWidget from '@girder/core/views/widgets/PluginConfigBreadcrumbWidget';
import View from '@girder/core/views/View';
import { restRequest } from '@girder/core/rest';

import ConfigViewTemplate from '../templates/configView.pug';

import ItemTagsWidget from './ItemTagsWidget';

var ConfigView = View.extend({

    render: function () {
        this.$el.html(ConfigViewTemplate({
            licenses: JSON.stringify(this.licenses, null, 4)
        }));
        restRequest({ url: 'system/setting', data: { key: 'item_tags.tag_list' }, method: 'GET' })
            .then((resp) => {
                this.itemTagsWidget = new ItemTagsWidget({
                    el: this.$el.find('.g-item-tags'),
                    tags: resp,
                    allowedTags: null,
                    accessLevel: AccessType.ADMIN,
                    parentView: this,
                    saveTags: this.saveTags.bind(this),
                    AccessType: AccessType
                });
                return true;
            });

        this.breadcrumb = new PluginConfigBreadcrumbWidget({
            pluginName: 'Item Tags',
            el: this.$('.g-config-breadcrumb-container'),
            parentView: this
        }).render();

        return this;
    },

    saveTags: function (tags) {
        tags = tags.sort();
        restRequest({ url: 'system/setting', data: { key: 'item_tags.tag_list', value: JSON.stringify(tags) }, method: 'PUT' })
            .then(() => {
                return this.render();
            });
    }
});

export default ConfigView;
