import UserView from 'girder/views/body/UserView';
import extendView from './extendView';

import Template from '../templates/userPoliciesMenu.jade';
extendView(UserView, Template, 'user');
