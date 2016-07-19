import extendView from './extendView';
import UserView from 'girder/views/body/UserView';

import UserViewPoliciesMenuTemplate from '../templates/userViewPoliciesMenu.jade';
extendView(UserView, UserViewPoliciesMenuTemplate, 'user');
