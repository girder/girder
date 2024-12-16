<!DOCTYPE html>
<html lang="en">
  <head>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>${brandName | h}</title>
    <link rel="stylesheet" href="${staticPublicPath}/built/girder_lib.min.css">
    <link rel="icon" type="image/png" href="${staticPublicPath}/built/Girder_Favicon.png">
    % for plugin in pluginCss:
    <link rel="stylesheet" href="${staticPublicPath}/built/plugins/${plugin}/plugin.min.css">
    % endfor
  </head>
  <body>
    <div id="g-global-info-apiroot" class="hide">${apiRoot}</div>
    <script src="${staticPublicPath}/built/girder_lib.min.js"></script>
    <script src="${staticPublicPath}/built/girder_app.min.js"></script>
    <script type="text/javascript">
        $(function () {
            girder.events.trigger('g:appload.before');
            girder.app = new girder.views.App({
                el: 'body',
                parentView: null,
                contactEmail: '${contactEmail | js}',
                privacyNoticeHref: '${privacyNoticeHref | js}',
                brandName: '${brandName | js}',
                bannerColor: '${bannerColor | js}',
                registrationPolicy: '${registrationPolicy | js}',
                enablePasswordLogin: ${enablePasswordLogin | n,json,js},
                downloadShown: '${downloadShown | js}'
            }).render();
            girder.events.trigger('g:appload.after', girder.app);
        });
    </script>
    % for plugin in pluginJs:
    <script src="${staticPublicPath}/built/plugins/${plugin}/plugin.min.js"></script>
    % endfor
  </body>
</html>
