/* eslint-env jquery */
$(function () {
    var apiRoot = $('#g-global-info-apiroot').text().replace(
        '%HOST%', window.location.origin);
    if (!apiRoot) {
        apiRoot = window.location.origin + window.location.pathname;
    }
    var swaggerUi = new window.SwaggerUIBundle({
        url: apiRoot + '/describe',
        dom_id: '#swagger-ui-container',
        supportHeaderParams: false,
        supportedSubmitMethods: ['get', 'post', 'put', 'delete', 'patch'],
        onComplete: function () {
            addApiKeyAuthorization();
        },
        onFailure: function (data) {
            if (console) {
                console.log('Unable to Load SwaggerUI');
                console.log(data);
            }
        },
        docExpansion: 'none',
        jsonEditor: false,
        apisSorter: 'alpha',
        operationsSorter: sortOperations,
        defaultModelRendering: 'model',
        showRequestHeaders: false,
        validatorUrl: null,
        tryItOutEnabled: true,
        defaultModelsExpandDepth: -1,
        deepLinking: true
    });

    var methodOrder = ['get', 'put', 'post', 'patch', 'delete'];

    // Comparator to sort operations by path and method.
    // Methods not in the pre-defined ordered list are placed at the end and
    // sorted alphabetically.
    function sortOperations(op1, op2) {
        var pathCmp = op1.get('path').localeCompare(op2.get('path'));
        if (pathCmp !== 0) {
            return pathCmp;
        }
        var index1 = methodOrder.indexOf(op1.get('method'));
        var index2 = methodOrder.indexOf(op2.get('method'));
        if (index1 > -1 && index2 > -1) {
            return index1 > index2 ? 1 : (index1 < index2 ? -1 : 0);
        }
        if (index1 > -1) {
            return -1;
        }
        if (index2 > -1) {
            return 1;
        }
        return op1.get('method').localeCompare(op2.get('method'));
    }

    function addApiKeyAuthorization() {
        const girderToken = window.localStorage.getItem('girderToken');
        if (girderToken) {
            swaggerUi.preauthorizeApiKey('Girder-Token', girderToken);
        }
    }
});
