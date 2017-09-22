girderTest.startApp();

describe('Test the model class', function () {
    var triggerRestError = false;

    beforeEach(function () {
        // Intercept window.location.assign calls so we can test the behavior of e.g. download
        // directives that occur from js.
        spyOn(window.location, 'assign');

        spyOn(girder.rest, 'restRequest').andCallFake(function (opts) {
            var resp = $.Deferred();
            if (triggerRestError) {
                resp.reject('err');
            } else {
                resp.resolve({});
            }
            return resp.promise();
        });
    });

    it('test the base model', function () {
        var SampleModel = girder.models.Model.extend({
            resourceName: 'sampleResource'
        });
        var id = '012345678901234567890123';

        var model = new SampleModel({});
        // test name
        model.set('name', 'sample');
        expect(model.name()).toBe('sample');
        // test increment
        expect(model.get('count')).toBe(undefined);
        model.set('count', 0);
        model.increment('count');
        expect(model.get('count')).toBe(1);
        model.increment('count');
        expect(model.get('count')).toBe(2);
        model.increment('count', 10);
        expect(model.get('count')).toBe(12);
        model.increment('count', 0);
        expect(model.get('count')).toBe(12);

        // test save
        model.resourceName = null;
        expect(model.save).toThrow();
        expect(girder.rest.restRequest.callCount).toBe(0);
        model.resourceName = 'sampleResource';
        model.save();
        expect(girder.rest.restRequest.callCount).toBe(1);
        expect(girder.rest.restRequest).toHaveBeenCalledWith({
            url: 'sampleResource',
            method: 'POST',
            data: {
                count: 12,
                name: 'sample'
            },
            error: null
        });

        // Test save to update
        girder.rest.restRequest.reset();
        model.set('_id', '012345678901234567890123');
        model.save();
        expect(girder.rest.restRequest.callCount).toBe(1);
        expect(girder.rest.restRequest).toHaveBeenCalledWith({
            url: 'sampleResource/012345678901234567890123',
            method: 'PUT',
            data: {
                count: 12,
                name: 'sample',
                _id: id
            },
            error: null
        });
        triggerRestError = true;
        model.save();
        expect(girder.rest.restRequest.callCount).toBe(2);
        triggerRestError = false;

        // test fetch
        girder.rest.restRequest.reset();
        model.resourceName = null;
        expect(_.bind(model.fetch, model)).toThrow();
        expect(girder.rest.restRequest.callCount).toBe(0);
        model.resourceName = 'sampleResource';
        model.fetch();
        expect(girder.rest.restRequest.callCount).toBe(1);
        expect(girder.rest.restRequest).toHaveBeenCalledWith({
            url: 'sampleResource/' + id
        });

        girder.rest.restRequest.reset();
        model.fetch({extraPath: 'abc'});
        expect(girder.rest.restRequest.callCount).toBe(1);
        expect(girder.rest.restRequest).toHaveBeenCalledWith({
            url: 'sampleResource/' + id + '/abc'
        });

        girder.rest.restRequest.reset();
        model.fetch({ignoreError: true});
        expect(girder.rest.restRequest.callCount).toBe(1);
        expect(girder.rest.restRequest).toHaveBeenCalledWith({
            url: 'sampleResource/' + id,
            error: null
        });

        girder.rest.restRequest.reset();
        model.fetch({data: {param1: 'value1'}});
        expect(girder.rest.restRequest.callCount).toBe(1);
        expect(girder.rest.restRequest).toHaveBeenCalledWith({
            url: 'sampleResource/' + id,
            data: {param1: 'value1'}
        });

        girder.rest.restRequest.reset();
        triggerRestError = true;
        model.fetch();
        expect(girder.rest.restRequest.callCount).toBe(1);
        triggerRestError = false;

        // test downloadUrl
        expect(model.downloadUrl()).toBe(girder.rest.apiRoot + '/sampleResource/' + id + '/download');
        expect(model.downloadUrl({foo: 'bar'})).toBe(girder.rest.apiRoot + '/sampleResource/' + id + '/download?foo=bar');

        // test download
        window.location.assign.reset();
        model.download();
        waitsFor(function () {
            return window.location.assign.wasCalled;
        }, 'redirect to the resource download URL');
        runs(function () {
            expect(window.location.assign)
                .toHaveBeenCalledWith(/^http:\/\/.*\/api\/v1\/sampleResource\/.+\/download$/);
        });

        // destroy
        girder.rest.restRequest.reset();
        model.resourceName = null;
        expect(_.bind(model.destroy, model)).toThrow();
        expect(girder.rest.restRequest.callCount).toBe(0);

        model.resourceName = 'sampleResource';
        model.destroy();
        expect(girder.rest.restRequest.callCount).toBe(1);
        expect(girder.rest.restRequest).toHaveBeenCalledWith({
            url: 'sampleResource/012345678901234567890123',
            method: 'DELETE',
            error: null
        });

        girder.rest.restRequest.reset();
        model.destroy({progress: true});
        expect(girder.rest.restRequest.callCount).toBe(1);
        expect(girder.rest.restRequest).toHaveBeenCalledWith({
            url: 'sampleResource/012345678901234567890123?progress=true',
            method: 'DELETE',
            error: null
        });

        girder.rest.restRequest.reset();
        model.destroy({throwError: false});
        expect(girder.rest.restRequest.callCount).toBe(1);
        expect(girder.rest.restRequest).toHaveBeenCalledWith({
            url: 'sampleResource/012345678901234567890123',
            method: 'DELETE'
        });

        girder.rest.restRequest.reset();
        triggerRestError = true;
        model.destroy();
        expect(girder.rest.restRequest.callCount).toBe(1);
        triggerRestError = false;

        // getAccessLevel
        expect(model.getAccessLevel()).toBe(undefined);
        model.set('_accessLevel', 'abc');
        expect(model.getAccessLevel()).toBe('abc');
    });
});
