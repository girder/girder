<!DOCTYPE html>
<html lang="en">
  <head>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>${title}</title>
    <link rel="stylesheet" href="//fonts.googleapis.com/css?family=Droid+Sans:400,700">
    <link rel="stylesheet" href="${staticRoot}/built/fontello/css/fontello.css">
    <link rel="stylesheet" href="${staticRoot}/built/swagger/css/reset.css">
    <link rel="stylesheet" href="${staticRoot}/built/swagger/css/screen.css">
    <link rel="stylesheet" href="${staticRoot}/built/swagger/docs.css">
    <link rel="icon" type="image/png" href="${staticRoot}/img/Girder_Favicon.png">
    <style type="text/css">
      .response_throbber {
        content: url("${staticRoot}/built/swagger/images/throbber.gif");
      }
      #api_info {
        display: none;
      }
    </style>
  </head>
  <body>
    <div class="docs-header">
      <span>Girder REST API Documentation</span>
      <i class="icon-book-alt right"></i>
      <div id="g-global-info-apiroot" style="display: none">${apiRoot}</div>
    </div>
    <div class="docs-body">
      <p>Below you will find the list of all of the resource types exposed by
      the Girder RESTful Web API. Click any of the resource links to open up a
      list of all available endpoints related to each resource type.</p>
      <p>Clicking any of those endpoints will display detailed documentation
      about the purpose of each endpoint and the input parameters and output
      values. You can also call API endpoints directly from this page by typing
      in the parameters you wish to pass and then clicking the "Try it out!"
      button.</p>
      <p><b>Warning:</b> This is not a sandbox&mdash;calls that you make from
      this page are the same as calling the API with any other client, so
      update or delete calls that you make will affect the actual data on the
      server.</p>
    </div>
    <div class="swagger-section">
      <div id="swagger-ui-container"
          class="swagger-ui-wrap docs-swagger-container">
      </div>
    </div>
    <script src="${staticRoot}/built/swagger/lib/jquery-1.8.0.min.js"></script>
    <script src="${staticRoot}/built/swagger/lib/jquery.slideto.min.js"></script>
    <script src="${staticRoot}/built/swagger/lib/jquery.wiggle.min.js"></script>
    <script src="${staticRoot}/built/swagger/lib/jquery.ba-bbq.min.js"></script>
    <script src="${staticRoot}/built/swagger/lib/handlebars-2.0.0.js"></script>
    <script src="${staticRoot}/built/swagger/lib/underscore-min.js"></script>
    <script src="${staticRoot}/built/swagger/lib/backbone-min.js"></script>
    <script src="${staticRoot}/built/swagger/swagger-ui.min.js"></script>
    <script src="${staticRoot}/built/swagger/lib/highlight.7.3.pack.js"></script>
    <script src='${staticRoot}/built/swagger/lib/jsoneditor.min.js'></script>
    <script src='${staticRoot}/built/swagger/lib/marked.js'></script>
    <script src="${staticRoot}/girder-swagger.js"></script>
    % if mode == 'testing':
    <script src="${staticRoot}/built/testing/testing.min.js"></script>
    % endif
  </body>
</html>
