$(function () {
    var apiRoot = $('#g-global-info-apiroot').text().replace(
        '%HOST%', window.location.origin);
    if (!apiRoot) {
        apiRoot = window.location.origin + window.location.pathname;
    }
    window.swaggerUi = new SwaggerUi({
        url: 'describe',
        dom_id: 'swagger-ui-container',
        supportHeaderParams: false,
        supportedSubmitMethods: ['get', 'post', 'put', 'delete'],
        onComplete: function (swaggerApi, swaggerUi) {
            $('pre code').each(function (i, e) {
                hljs.highlightBlock(e);
            });
        },
        onFailure: function (data) {
            if (console) {
                console.log("Unable to Load SwaggerUI");
                console.log(data);
            }
        },
        docExpansion: "none"
    });

    var cookieParams = document.cookie.split(';').map(function (m) {
        return m.replace(/^\s+/, '').replace(/\s+$/, '');
    });
    $.each(cookieParams, function (i, val) {
        var arr = val.split('=');
        if (arr[0] === 'girderToken') {
            // Make swagger send the Girder-Token header with each request.
            window.authorizations.add("key",
                new ApiKeyAuthorization("Girder-Token", arr[1], "header"));
        }
    });

    swaggerUi.load();
});
