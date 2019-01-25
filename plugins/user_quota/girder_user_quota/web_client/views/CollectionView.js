import CollectionView from '@girder/core/views/body/CollectionView';

import CollectionViewPoliciesMenuTemplate from '../templates/collectionViewPoliciesMenu.pug';

import extendView from './extendView';

extendView(CollectionView, CollectionViewPoliciesMenuTemplate, 'collection');
