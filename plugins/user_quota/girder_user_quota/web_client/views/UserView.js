import UserView from '@girder/core/views/body/UserView';

import UserViewPoliciesMenuTemplate from '../templates/userViewPoliciesMenu.pug';

import extendView from './extendView';

extendView(UserView, UserViewPoliciesMenuTemplate, 'user');
