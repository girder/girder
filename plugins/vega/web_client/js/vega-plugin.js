var vegaPlugin = {
    views: {}
};

vegaPlugin.views.VegaWidget = girder.View.extend({
    initialize: function (settings) {
        this.item = settings.item;
        this.accessLevel = settings.accessLevel;
        this.item.on('change', function () {
            this.render();
        }, this);
        this.render();
    },

    render: function () {
        var meta = this.item.get('meta');

        if (this.accessLevel >= girder.AccessType.READ && meta && meta.vega) {
            $("#g-app-body-container")
                .append(girder.templates.vega_render());
            $.ajax({
                url: "/api/v1/item/" + this.item.get("_id") + "/download",
                type: "GET",
                dataType: "json",
                success: function (spec) {
                    vg.parse.spec(spec, function (chart) {
                        chart({
                            el: ".g-item-vega-vis",
                            renderer: "svg"
                        }).update();
                    });
                }
            });
        } else {
            $(".g-item-vega")
                .remove();
        }
    }
});

girder.wrap(girder.views.ItemView, 'render', function (render) {
    this.model.getAccessLevel(_.bind(function (accessLevel) {
        // Because the passthrough call to render() also does an async call to
        // getAccessLevel(), wait until this one completes before invoking that
        // one.
        //
        // Furthermore, we need to call this *first*, because of how the Vega
        // view inserts itself into the app-body-container, which doesn't seem
        // to exist until the passthrough call is made.
        render.call(this);

        this.vegaWidget = new vegaPlugin.views.VegaWidget({
            item: this.model,
            accessLevel: accessLevel,
            parentView: this
        });

    }, this));

    return this;
});
