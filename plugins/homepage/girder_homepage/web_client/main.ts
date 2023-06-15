import { Girder } from '@girder/core';
import { initRoutes } from './routes';
import { initFrontPageView } from './views/FrontPageView';

export const dependencies = [
  '@girder/dummy-dependency',
];

export const init = (girder: Girder) => {
  initRoutes(girder);
  initFrontPageView(girder);
};
