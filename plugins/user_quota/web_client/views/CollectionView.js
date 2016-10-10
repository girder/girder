import CollectionView from 'girder/views/body/CollectionView';
import extendView from './extendView';

import CollectionViewPoliciesMenuTemplate from '../templates/collectionViewPoliciesMenu.pug';
extendView(CollectionView, CollectionViewPoliciesMenuTemplate, 'collection');
