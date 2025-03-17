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
          deepLinking: true
        });
      })();
    </script>
  </body>
</html>
