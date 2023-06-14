import { initRoutes } from './routes';
import { initFrontPageView } from './views/FrontPageView';

export const dependencies = [
  '@girder/dummy-dependency',
];

export const init = (girder) => {
  initRoutes(girder);
  initFrontPageView(girder);
};
