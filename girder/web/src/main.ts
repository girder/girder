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

  const scriptPromises: Promise<void>[] = [];
  staticFiles.js.forEach((href) => {
    scriptPromises.push(new Promise((resolve) => {
      const script = document.createElement('script');
      script.type = 'text/javascript';
      script.src = new URL(href, origin).href;
      document.head.appendChild(script);
      script.addEventListener('load', function() {
        resolve();
      });
    }));
  });

  await Promise.all(scriptPromises);
  await girder.initializeDefaultApp(apiRoot);
})();
