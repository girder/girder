import _ from 'underscore';

import events from '@girder/core/events';
import CollectionModel from '@girder/core/models/CollectionModel';
import FolderModel from '@girder/core/models/FolderModel';
import ItemModel from '@girder/core/models/ItemModel';
import CollectionView from '@girder/core/views/body/CollectionView';
import FolderView from '@girder/core/views/body/FolderView';
import ItemView from '@girder/core/views/body/ItemView';

import TermsAcceptanceView from './views/TermsAcceptanceView';

CollectionView.fetchAndInit = function (cid, params) {
    const collection = new CollectionModel({_id: cid});
    collection.fetch()
        .done(() => {
            if (collection.hasTerms() && !collection.currentUserHasAcceptedTerms()) {
                events.trigger(
                    'g:navigateTo',
                    TermsAcceptanceView,
                    {collection: collection}
                );
            } else {
                events.trigger(
                    'g:navigateTo',
                    CollectionView,
                    _.extend({collection: collection}, params || {})
                );
            }
        });
};

FolderView.fetchAndInit = function (id, params) {
    let collection;
    const folder = new FolderModel({_id: id});
    folder.fetch()
        .then(() => {
            if (folder.get('baseParentType') === 'collection') {
                collection = new CollectionModel({_id: folder.get('baseParentId')});
                return collection.fetch();
            } else {
                return undefined;
            }
        })
        .done(() => {
            if (collection && collection.hasTerms() && !collection.currentUserHasAcceptedTerms()) {
                events.trigger(
                    'g:navigateTo',
                    TermsAcceptanceView,
                    {collection: collection}
                );
            } else {
                events.trigger(
                    'g:navigateTo',
                    FolderView,
                    _.extend({folder: folder}, params || {})
                );
            }
        });
};

ItemView.fetchAndInit = function (itemId, params) {
    let collection;
    const item = new ItemModel({_id: itemId});
    item.fetch()
        .then(() => {
            if (item.get('baseParentType') === 'collection') {
                collection = new CollectionModel({_id: item.get('baseParentId')});
                return collection.fetch();
            } else {
                return undefined;
            }
        })
        .done(() => {
            if (collection && collection.hasTerms() && !collection.currentUserHasAcceptedTerms()) {
                events.trigger(
                    'g:navigateTo',
                    TermsAcceptanceView,
                    {collection: collection}
                );
            } else {
                events.trigger(
                    'g:navigateTo',
                    ItemView,
                    _.extend({item: item}, params || {})
                );
            }
        });
};
