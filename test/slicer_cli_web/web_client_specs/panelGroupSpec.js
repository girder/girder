girderTest.importPlugin('jobs', 'worker', 'slicer_cli_web');

var slicer;
girderTest.promise.done(function () {
    slicer = girder.plugins.slicer_cli_web;
});

describe('panel group', function () {
    var $el, admin, parentView = {
        registerChildView: function () { }
    };

    beforeEach(function () {
        admin = new girder.models.UserModel({ _id: 'admin', name: 'admin' });
        $el = $('<div/>').appendTo('body');
    });

    afterEach(function () {
        $el.remove();
    });

    // test different widget types
    it('panel group', function () {
        var w = new slicer.views.PanelGroup({
            closeButton: true,
            parentView: parentView,
            el: $el.get(0)
        });

        var xml = '' +
        '<?xml version="1.0" encoding="UTF-8" ?>'+
        '<executable>'+
        '  <category>Example</category>'+
        '  <title>Simple Example</title>' +
        '  <description>Report on a few input parameters.</description>' +
        '  <version>0.1.0</version>' +
        '  <license>Apache 2.0</license>' +
        '  <contributor>David Manthey (Kitware)</contributor>' +
        '  <parameters>' +
        '    <label>IO</label>' +
        '    <description>Input/output parameters.</description>' +
        '    <image>' +
        '      <name>ImageFile</name>' +
        '      <label>Input Image</label>' +
        '      <channel>input</channel>' +
        '      <description>Input image</description>' +
        '      <index>0</index>' +
        '    </image>' +
        '    <double-vector>' +
        '      <name>Color1</name>' +
        '      <label>RGB Color</label>' +
        '      <description>An RGB Color Vector</description>' +
        '      <channel>input</channel>' +
        '      <index>1</index>' +
        '    </double-vector>' +
        '    <double-vector>' +
        '      <name>Color2</name>' +
        '      <label>YCbCr Color</label>' +
        '      <description>A YCBCr Color Vector</description>' +
        '      <channel>input</channel>' +
        '      <index>2</index>' +
        '    </double-vector>' +
        '  </parameters>' +
        '</executable>';

        w.render();

        expect(w.$el.hasClass('hidden')).toBe(true);

        runs(function () {
            w.setAnalysis('/test', xml);
        });
        waitsFor(function () {
            return w.panels.length > 0;
        });
        runs(function () {
            expect(w.panels.length).toBe(1);
        });
    });
});
