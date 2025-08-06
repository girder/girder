<!DOCTYPE html>
<html lang="en">
  <head>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>${brandName | h} - REST API Documentation</title>
    <link rel="stylesheet" href="https://unpkg.com/swagger-ui-dist@5.20.1/swagger-ui.css">
    <link rel="icon" type="image/png" href="/Girder_Favicon.png">
    <script src="https://unpkg.com/swagger-ui-dist@5.20.1/swagger-ui-bundle.js"></script>
  </head>
  <body>
    <div id="swagger-ui-container"></div>
    <script type="text/javascript">
      (function () {
        var swaggerUi = new window.SwaggerUIBundle({
          url: '/api/v1/describe',
          dom_id: '#swagger-ui-container',
          docExpansion: 'none',
          defaultModelRendering: 'model',
          validatorUrl: null,
          defaultModelsExpandDepth: -1,
          deepLinking: true,
          tryItOutEnabled: true,
          apisSorter: 'alpha',
          operationsSorter: (op1, op2) => {
            // Comparator to sort operations by path and method.
            // Methods not in the pre-defined ordered list are placed at the
            // end and sorted alphabetically.
            var methodOrder = ['get', 'put', 'post', 'patch', 'delete'];
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
          },
          onComplete: function () {
           const girderToken = window.localStorage.getItem('girderToken');
            if (girderToken) {
              swaggerUi.preauthorizeApiKey('Girder-Token', girderToken);
            }
          }
        });
      })();
    </script>
  </body>
</html>
