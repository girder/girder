import extendView from './extendView';
import UserView from 'girder/views/body/UserView';

import UserViewPoliciesMenuTemplate from '../templates/userViewPoliciesMenu.pug';
extendView(UserView, UserViewPoliciesMenuTemplate, 'user');
