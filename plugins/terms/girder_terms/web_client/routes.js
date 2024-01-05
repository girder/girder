import TermsAcceptanceView from './views/TermsAcceptanceView';

const _ = girder._;
const events = girder.events;
const CollectionView = girder.views.body.CollectionView;
const FolderView = girder.views.body.FolderView;
const ItemView = girder.views.body.ItemView;
const CollectionModel = girder.models.CollectionModel;
const FolderModel = girder.models.FolderModel;
const ItemModel = girder.models.ItemModel;

CollectionView.fetchAndInit = function (cid, params) {
    const collection = new CollectionModel({ _id: cid });
    collection.fetch()
        .done(() => {
            if (collection.hasTerms() && !collection.currentUserHasAcceptedTerms()) {
                events.trigger(
                    'g:navigateTo',
                    TermsAcceptanceView,
                    { collection: collection }
                );
            } else {
                events.trigger(
                    'g:navigateTo',
                    CollectionView,
                    _.extend({ collection: collection }, params || {})
                );
            }
        });
};

FolderView.fetchAndInit = function (id, params) {
    let collection;
    const folder = new FolderModel({ _id: id });
    folder.fetch()
        .then(() => {
            if (folder.get('baseParentType') === 'collection') {
                collection = new CollectionModel({ _id: folder.get('baseParentId') });
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
                    { collection: collection }
                );
            } else {
                events.trigger(
                    'g:navigateTo',
                    FolderView,
                    _.extend({ folder: folder }, params || {})
                );
            }
        });
};

ItemView.fetchAndInit = function (itemId, params) {
    let collection;
    const item = new ItemModel({ _id: itemId });
    item.fetch()
        .then(() => {
            if (item.get('baseParentType') === 'collection') {
                collection = new CollectionModel({ _id: item.get('baseParentId') });
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
                    { collection: collection }
                );
            } else {
                events.trigger(
                    'g:navigateTo',
                    ItemView,
                    _.extend({ item: item }, params || {})
                );
            }
        });
};
