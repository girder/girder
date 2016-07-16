import CollectionView from 'girder/views/body/CollectionView';
import extendView from './extendView';

import Template from '../templates/collectionPoliciesMenu.jade';
extendView(CollectionView, Template, 'collection');
