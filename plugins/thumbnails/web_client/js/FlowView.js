girder.views.thumbnails_FlowView = girder.View.extend({
    events: {
        'click .g-thumbnail-delete': function (e) {
            var container = $(e.currentTarget).parents('.g-thumbnail-container');
            var file = new girder.models.FileModel({_id: container.attr('g-file-id')});

            girder.confirm({
                text: 'Are you sure you want to delete this thumbnail?',
                yesText: 'Delete',
                confirmCallback: _.bind(function () {
                    file.on('g:deleted', function () {
                        container.remove();
                    }).on('g:error', function () {
                        girder.events.trigger('g:alert', {
                            icon: 'cancel',
                            text: 'Failed to delete thumbnail.',
                            type: 'danger',
                            timeout: 4000
                        });
                    }).destroy();
                }, this)
            });
        }
    },

    initialize: function (settings) {
        this.thumbnails = settings.thumbnails;
        this.accessLevel = settings.accessLevel || girder.AccessType.READ;
    },

    render: function () {
        this.$el.html(girder.templates.thumbnails_flowView({
            thumbnails: this.thumbnails,
            accessLevel: this.accessLevel,
            girder: girder
        }));

        this.$('.g-thumbnail-actions-container a').tooltip({
            delay: 100
        });

        this.$('.g-thumbnail-container').hover(function () {
            $('.g-thumbnail-actions-container', this).addClass('g-show');
        }, function () {
            $('.g-thumbnail-actions-container', this).removeClass('g-show');
        });
    }
});
