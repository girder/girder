<!DOCTYPE html>
<html lang="en">
  <head>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>${title}</title>
    <link rel="stylesheet" href="//fonts.googleapis.com/css?family=Droid+Sans:400,700">
    <link rel="stylesheet" href="${staticRoot}/built/fontello/css/fontello.css">
    <link rel="stylesheet" href="${staticRoot}/built/fontello/css/animation.css">
    <link rel="stylesheet" href="${staticRoot}/built/girder.app.min.css">
    <link rel="icon" type="image/png" href="${staticRoot}/img/Girder_Favicon.png">
  </head>
  <body>
    <div id="g-global-info-apiroot" class="hide">${apiRoot}</div>
    <div id="g-global-info-staticroot" class="hide">${staticRoot}</div>
    <script src="${staticRoot}/built/girder.app.min.js"></script>
    <script>
      girder.events.trigger('g:appload.before');
      new girder.views.App({
        el: 'body',
        parentView: null
      });
      girder.events.trigger('g:appload.after');
    </script>
  </body>
</html>
