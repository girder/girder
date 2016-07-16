import UserView from 'girder/views/body/UserView';
import extendView from './extendView';

import UserViewPoliciesMenuTemplate from '../templates/userViewPoliciesMenu.jade';
extendView(UserView, UserViewPoliciesMenuTemplate, 'user');
