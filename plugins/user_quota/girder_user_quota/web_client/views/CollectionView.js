import CollectionViewPoliciesMenuTemplate from '../templates/collectionViewPoliciesMenu.pug';

import extendView from './extendView';

const CollectionView = girder.views.body.CollectionView;

extendView(CollectionView, CollectionViewPoliciesMenuTemplate, 'collection');
