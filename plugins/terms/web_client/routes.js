import _ from 'underscore';

import events from 'girder/events';
import CollectionModel from 'girder/models/CollectionModel';
import FolderModel from 'girder/models/FolderModel';
import ItemModel from 'girder/models/ItemModel';
import CollectionView from 'girder/views/body/CollectionView';
import FolderView from 'girder/views/body/FolderView';
import ItemView from 'girder/views/body/ItemView';

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
