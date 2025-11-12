import { girder } from '.';

declare global {
  interface Window {
    girder: typeof girder;
  }
}
window.girder = girder;

interface StaticFilesSpec {
  css: string[],
  js: string[],
}

let apiRoot = import.meta.env.VITE_API_ROOT;
let pluginRoot = import.meta.env.VITE_GIRDER_PLUGIN_ROOT;

(async () => {
  if (!apiRoot) {
    const appElement = document.getElementById('app');
    apiRoot = (appElement && appElement.getAttribute('root')) || '';
    apiRoot += (apiRoot.endsWith('/') ? '' : '/') + 'api/v1';
    if (!apiRoot.startsWith('/') && apiRoot.indexOf(':') < 0) {
        apiRoot = '/' + apiRoot;
    }
  }

  const staticFilesResp = await fetch(`${apiRoot}/system/plugin_static_files`);
  const staticFiles: StaticFilesSpec = await staticFilesResp.json();

  // The plugin root defaults to the location of the client app
  // That is correct for most deployments but if girder is being served from a different base path compared to the api
  // then the plugin root must be set explicitly via an environment variable at build time.
  if (!pluginRoot) {
    // Check and see if the api root matches the location of the client app
    const appElement = document.getElementById('app');
    const baseApiPath = (appElement && appElement.getAttribute('root')) || '';
    const baseAppPath = window.location.href.replace(window.location.origin, '');
    if (baseAppPath.includes(baseApiPath)) {
      // Adjust the plugin root to use the same base path as the api root
      pluginRoot = window.location.origin + baseApiPath;
    }
  }


  staticFiles.css.forEach((href) => {
    const link = document.createElement('link');
    link.rel = 'stylesheet';
    link.type = 'text/css';
    link.href = new URL(href, pluginRoot).href;
    document.head.appendChild(link);
  });



  // Since plugin JS files may implicitly depend on each other at import time, we can't load
  // them in parallel. They already come to us in topoligically sorted order, so we can safely
  // load them one after the other.
  for (const href of staticFiles.js) {
    await new Promise<void>((resolve) => {
      const script = document.createElement('script');
      script.type = 'text/javascript';
      script.src = new URL(href, pluginRoot).href;
      document.head.appendChild(script);
      script.addEventListener('load', function() {
        resolve();
      });
    });
  };

  await girder.initializeDefaultApp(apiRoot);
})();
