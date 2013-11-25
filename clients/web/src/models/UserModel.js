girder.models.UserModel = girder.Model.extend({
    resourceName: 'user',

    name: function () {
        return this.get('firstName') + ' ' + this.get('lastName');
    }
});
