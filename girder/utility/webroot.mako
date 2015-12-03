<!DOCTYPE html>
<html lang="en">
  <head>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>${title}</title>
    <link rel="stylesheet" href="//fonts.googleapis.com/css?family=Droid+Sans:400,700">
    <link rel="stylesheet" href="${staticRoot}/lib/bootstrap/css/bootstrap.min.css">
    <link rel="stylesheet" href="${staticRoot}/lib/bootstrap/css/bootstrap-switch.min.css">
    <link rel="stylesheet" href="${staticRoot}/lib/fontello/css/fontello.css">
    <link rel="stylesheet" href="${staticRoot}/lib/fontello/css/animation.css">
    <link rel="stylesheet" href="${staticRoot}/built/jsoneditor/jsoneditor.min.css">
    <link rel="stylesheet" href="${staticRoot}/lib/jqplot/css/jquery.jqplot.min.css">
    <link rel="stylesheet" href="${staticRoot}/built/app.min.css">
    <link rel="icon" type="image/png" href="${staticRoot}/img/Girder_Favicon.png">
    % for plugin in pluginCss:
    <link rel="stylesheet" href="${staticRoot}/built/plugins/${plugin}/plugin.min.css">
    % endfor
  </head>
  <body>
    <div id="g-global-info-apiroot" class="hide">${apiRoot}</div>
    <div id="g-global-info-staticroot" class="hide">${staticRoot}</div>
    <script src="${staticRoot}/built/libs.min.js"></script>
    <script src="${staticRoot}/built/app.min.js"></script>
    <script src="${staticRoot}/built/main.min.js"></script>
    % for plugin in pluginJs:
    <script src="${staticRoot}/built/plugins/${plugin}/plugin.min.js"></script>
    % endfor
  </body>
</html>
