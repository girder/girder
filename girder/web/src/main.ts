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
  let origin = window.origin;

  try {
    // This will raise an exception if apiRoot is relative
    origin = new URL(apiRoot).origin;
  } catch {}

  const staticFilesResp = await fetch(`${apiRoot}/system/plugin_static_files`);
  const staticFiles: StaticFilesSpec = await staticFilesResp.json();

  staticFiles.css.forEach((href) => {
    const link = document.createElement('link');
    link.rel = 'stylesheet';
    link.type = 'text/css';
    link.href = new URL(href, origin).href;
    document.head.appendChild(link);
  });

  staticFiles.js.forEach((href) => {
    const script = document.createElement('script');
    script.type = 'text/javascript';
    script.src = new URL(href, origin).href;
    document.head.appendChild(script);
  })

  await girder.initializeDefaultApp(apiRoot);
})();
