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

const apiRoot = process.env.API_ROOT ?? '/api/v1';

(async () => {
  const staticFilesResp = await fetch(`${apiRoot}/system/plugin_static_files`);
  const staticFiles: StaticFilesSpec = await staticFilesResp.json();

  staticFiles.css.forEach((href) => {
    const link = document.createElement('link');
    link.rel = 'stylesheet';
    link.type = 'text/css';
    link.href = href;
    document.head.appendChild(link);
  });

  staticFiles.js.forEach((src) => {
    const script = document.createElement('script');
    script.type = 'text/javascript';
    script.src = src;
    document.head.appendChild(script);
  })

  await girder.initializeDefaultApp(apiRoot);
})();
