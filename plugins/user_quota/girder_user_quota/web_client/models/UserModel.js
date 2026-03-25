import extendModel from './extendModel';

const UserModel = girder.models.UserModel;

extendModel(UserModel, 'user');
