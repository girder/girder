import CollectionView from 'girder/views/body/CollectionView';
import extendView from './extendView';

import CollectionViewPoliciesMenuTemplate from '../templates/collectionViewPoliciesMenu.jade';
extendView(CollectionView, CollectionViewPoliciesMenuTemplate, 'collection');
