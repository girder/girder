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
        supportedSubmitMethods: ['get', 'post', 'put', 'delete', 'patch'],
        onComplete: function (swaggerApi, swaggerUi) {
            $('pre code').each(function (i, e) {
                hljs.highlightBlock(e);
            });

            addApiKeyAuthorization();
        },
        onFailure: function (data) {
            if (console) {
                console.log("Unable to Load SwaggerUI");
                console.log(data);
            }
        },
        docExpansion: "none",
        jsonEditor: false,
        apisSorter: "alpha",
        operationsSorter: sortOperations,
        defaultModelRendering: "schema",
        showRequestHeaders: false,
        validatorUrl: null
    });

    var methodOrder = ['get', 'put', 'post', 'patch', 'delete'];

    // Comparator to sort operations by path and method.
    // Methods not in the pre-defined ordered list are placed at the end and
    // sorted alphabetically.
    function sortOperations(op1, op2) {
        var pathCmp = op1.path.localeCompare(op2.path);
        if (pathCmp !== 0) {
            return pathCmp;
        }
        var index1 = methodOrder.indexOf(op1.method);
        var index2 = methodOrder.indexOf(op2.method);
        if (index1 > -1 && index2 > -1) {
            return index1 > index2 ? 1 : (index1 < index2 ? -1 : 0);
        }
        if (index1 > -1) {
            return -1;
        }
        if (index2 > -1) {
            return 1;
        }
        return op1.method.localeCompare(op2.method);
    }

    function addApiKeyAuthorization() {
        var cookieParams = document.cookie.split(';').map(function (m) {
            return m.replace(/^\s+/, '').replace(/\s+$/, '');
        });
        $.each(cookieParams, function (i, val) {
            var arr = val.split('=');
            if (arr[0] === 'girderToken') {
                // Make swagger send the Girder-Token header with each request.
                var apiKeyAuth = new SwaggerClient.ApiKeyAuthorization(
                    "Girder-Token", arr[1], "header");
                window.swaggerUi.api.clientAuthorizations.add(
                    "Girder-Token", apiKeyAuth);
            }
        });
    }

    window.swaggerUi.load();
});
