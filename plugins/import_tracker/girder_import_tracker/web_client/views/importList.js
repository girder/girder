import $ from 'jquery';
import moment from 'moment';

import PaginateWidget from '@girder/core/views/widgets/PaginateWidget';
import Collection from '@girder/core/collections/Collection';

import AssetstoreModel from '@girder/core/models/AssetstoreModel';
import { SORT_DESC } from '@girder/core/constants';
import View from '@girder/core/views/View';
import router from '@girder/core/router';
import { restRequest } from '@girder/core/rest';

import importListTemplate from '../templates/importList.pug';
import '../stylesheets/importList.styl';

var importList = View.extend({
    events: {
        'click .re-import-btn': function (e) {
            const index = Number($(e.currentTarget).attr('index'));
            const importEvent = this.imports[index];
            if (importEvent === undefined) {
                return;
            }

            // Re-perform import
            const assetstore = new AssetstoreModel({ _id: importEvent.get('assetstoreId') });
            const destType = importEvent.get('params').destinationType;
            const destId = importEvent.get('params').destinationId;

            assetstore.off('g:imported').on('g:imported', function () {
                router.navigate(destType + '/' + destId, { trigger: true });
            }, this).on('g:error', function (resp) {
                this.$('.g-validation-failed-message').text(resp.responseJSON.message);
            }, this);

            assetstore.once('g:fetched', () => {
                assetstore.import(importEvent.get('params'));
            }).fetch();
        },
        'click .re-import-edit-btn': function (e) {
            const index = Number($(e.currentTarget).attr('index'));
            const importEvent = this.imports[index];
            if (importEvent === undefined) {
                return;
            }

            // Navigate to re-import page
            const navigate = (assetstoreId, importId) => {
                const assetstore = new AssetstoreModel({ _id: assetstoreId });
                assetstore.once('g:fetched', () => {
                    router.navigate(`assetstore/${assetstoreId}/re-import/${importId}`, { trigger: true });
                }).fetch();
            };

            const assetstoreId = importEvent.get('assetstoreId');
            const importId = importEvent.get('_id');
            navigate(assetstoreId, importId);
        }
    },

    initialize({ id, unique }) {
        this._unique = unique;
        this._assetstoreId = id;
        this.imports = [];

        const route = id ? `${id}/imports` : 'all_imports';
        this.collection = new Collection();
        this.collection.altUrl = `assetstore/${route}`;
        this.collection.sortField = 'started';
        this.collection.sortDir = SORT_DESC;
        this.collection.params = { unique: unique || false };

        this.listenTo(this.collection, 'update reset', this._updateData);

        this.paginateWidget = new PaginateWidget({
            collection: this.collection,
            parentView: this
        });

        restRequest({
            url: 'assetstore',
            data: { limit: 0 }
        }).done((result) => {
            this.assetstores = result.map((a) => a._id);

            this.collection.fetch({}, true);
        });
    },

    _updateData() {
        this.imports = this.collection.toArray();
        this.render();
    },

    render() {
        this.$el.html(importListTemplate({
            imports: this.imports,
            assetstores: this.assetstores,
            moment: moment,
            unique: this._unique,
            assetstoreId: this._assetstoreId
        }));
        this.$el.tooltip();

        this.paginateWidget.setElement(this.$('.g-imports-pagination')).render();

        return this;
    }
});

export default importList;
