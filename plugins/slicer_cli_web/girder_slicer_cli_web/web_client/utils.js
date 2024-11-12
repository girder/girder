const $ = girder.$;
const _ = girder._;
const { restRequest } = girder.rest;
const utils = {};

utils.handleDatalist = function (elem, basePath, getParams) {
    if (!utils.handleDatalist._existing) {
        utils.handleDatalist._existing = $.Deferred().resolve();
    }
    utils.handleDatalist._existing.always(() => {
        utils.handleDatalist._existing = undefined;
        const params = getParams();
        _.each(params, function (value, key) {
            if (Array.isArray(value)) {
                params[key] = JSON.stringify(value);
            }
        });
        const promises = elem.find('.has-datalist[id]').map((idx, el) => {
            const id = $(el).attr('id');
            restRequest({
                url: basePath + '/datalist/' + id,
                method: 'POST',
                data: params
            }).then((data) => {
                $(el).find('datalist').remove();
                $(el).removeAttr('list');
                const elements = $(data).filter('element');
                if (elements.length) {
                    const dl = $('<datalist>').attr('id', id + '_datalist');
                    elements.each((idx, entry) => dl.append($('<option>').attr('value', $(entry).text())));
                    $(el).append(dl);
                    $(el).attr('list', id + '_datalist');
                }
                return null;
            });
        });
        utils.handleDatalist._existing = $.when.apply($, promises).always(() => {
            utils.handleDatalist._existing = undefined;
            return null;
        });
    });
};

export default utils;
