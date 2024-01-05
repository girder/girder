import UserViewPoliciesMenuTemplate from '../templates/userViewPoliciesMenu.pug';
import extendView from './extendView';

const UserView = girder.views.body.UserView;

extendView(UserView, UserViewPoliciesMenuTemplate, 'user');
