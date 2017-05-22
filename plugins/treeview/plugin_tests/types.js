/* global girder girderTest describe it expect beforeEach _ */

girderTest.addCoveredScripts([
    '/clients/web/static/built/plugins/treeview/plugin.min.js'
]);

girderTest.importStylesheet('/static/built/plugins/treeview/plugin.min.css');

describe('treeview type registry', function () {
    var treeview;
    beforeEach(function () {
        treeview = girder.plugins.treeview;
    });
    it('register a new type', function () {
        var load = _.noop;
        var parent = _.noop;
        var children = _.noop;
        var options = {
            icon: 'icon-test'
        };

        treeview.types.register('testtype', load, parent, children, options);
        var def = treeview.types.getDefinition('testtype');

        expect(def.load).toBe(load);
        expect(def.parent).toBe(parent);
        expect(def.children).toBe(parent);
        expect(def.options).toBe(options);
        expect(treeview.types.icons.testtype).toEqual({icons: 'icon-test'});
    });
});
