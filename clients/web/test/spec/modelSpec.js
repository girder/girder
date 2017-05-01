/**
 * Start the girder backbone app.
 */
girderTest.startApp();

describe('Test the model class', function () {
    var lastRequest, triggerRestError = false, requestCount = 0,
        windowAlert, lastAlert, alertCount = 0;

    beforeEach(function () {
        girder.rest.mockRestRequest(function (opts) {
            requestCount += 1;
            lastRequest = opts;
            var resp = $.Deferred();
            if (triggerRestError) {
                resp.reject('err');
            } else {
                resp.resolve({});
            }
            // The jqXHR response of a rest request needs an error function
            resp.error = resp.fail;
            return resp;
        });

        windowAlert = window.alert;
        window.alert = function (msg) {
            lastAlert = msg;
            alertCount += 1;
        };
    });

    afterEach(function () {
        girder.rest.unmockRestRequest();
        window.alert = windowAlert;
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
        expect(alertCount).toBe(0);
        model.resourceName = null;
        model.save();
        expect(alertCount).toBe(1);
        expect(lastAlert.indexOf('You must set')).toBeGreaterThan(0);
        model.resourceName = 'sampleResource';
        expect(requestCount).toBe(0);
        model.save();
        expect(requestCount).toBe(1);
        expect(lastRequest.type).toBe('POST');
        expect(lastRequest.data).toEqual({count: 12, name: 'sample'});
        model.set('_id', '012345678901234567890123');
        model.save();
        expect(requestCount).toBe(2);
        expect(lastRequest.type).toBe('PUT');
        expect(lastRequest.data).toEqual({
            count: 12, name: 'sample', _id: id});
        triggerRestError = true;
        model.save();
        expect(requestCount).toBe(3);
        triggerRestError = false;
        // test fetch
        requestCount = 0;
        model.resourceName = null;
        model.fetch();
        expect(alertCount).toBe(2);
        expect(lastAlert.indexOf('You must set')).toBeGreaterThan(0);
        model.resourceName = 'sampleResource';
        model.fetch();
        expect(requestCount).toBe(1);
        expect(lastRequest.type).toBe(undefined);
        expect(lastRequest.path).toBe('sampleResource/' + id);
        expect(lastRequest.error).toBe(undefined);
        expect(lastRequest.data).toBe(undefined);
        model.fetch({extraPath: 'abc'});
        expect(requestCount).toBe(2);
        expect(lastRequest.path).toBe('sampleResource/' + id + '/abc');
        expect(lastRequest.error).toBe(undefined);
        expect(lastRequest.data).toBe(undefined);
        model.fetch({ignoreError: true});
        expect(requestCount).toBe(3);
        expect(lastRequest.path).toBe('sampleResource/' + id);
        expect(lastRequest.error).toBe(null);
        expect(lastRequest.data).toBe(undefined);
        model.fetch({data: {param1: 'value1'}});
        expect(requestCount).toBe(4);
        expect(lastRequest.path).toBe('sampleResource/' + id);
        expect(lastRequest.error).toBe(undefined);
        expect(lastRequest.data).toEqual({param1: 'value1'});
        triggerRestError = true;
        model.fetch();
        expect(requestCount).toBe(5);
        triggerRestError = false;
    });
});
