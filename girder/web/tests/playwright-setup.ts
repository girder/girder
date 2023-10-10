import fs from 'fs';

import { PlaywrightTestConfig } from "@playwright/test";

// eslint-disable-next-line @typescript-eslint/no-unused-vars
export default (_config: PlaywrightTestConfig) => {
  if (fs.existsSync("coverage")) {
    fs.rmSync("coverage", { recursive: true, force: true });
  }
  fs.mkdirSync("coverage/data", { recursive: true });
};
