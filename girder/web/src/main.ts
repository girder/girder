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

const apiRoot = import.meta.env.VITE_API_ROOT ?? '/api/v1';

(async () => {
  const origin = apiRoot.startsWith('/') ? window.origin : new URL(apiRoot).origin;
  const staticFilesResp = await fetch(`${apiRoot}/system/plugin_static_files`);
  const staticFiles: StaticFilesSpec = await staticFilesResp.json();

  staticFiles.css.forEach((href) => {
    const link = document.createElement('link');
    link.rel = 'stylesheet';
    link.type = 'text/css';
    link.href = new URL(href, origin).href;
    document.head.appendChild(link);
  });

  // Since plugin JS files may implicitly depend on each other at import time, we can't load
  // them in parallel. They already come to us in topoligically sorted order, so we can safely
  // load them one after the other.
  for (const href of staticFiles.js) {
    await new Promise<void>((resolve) => {
      const script = document.createElement('script');
      script.type = 'text/javascript';
      script.src = new URL(href, origin).href;
      document.head.appendChild(script);
      script.addEventListener('load', function() {
        resolve();
      });
    });
  };

  await girder.initializeDefaultApp(apiRoot);
})();
