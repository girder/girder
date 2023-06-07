import { PlaywrightTestConfig } from "@playwright/test";
import fs from 'fs';

export default (_config: PlaywrightTestConfig) => {
  if (fs.existsSync("coverage")) {
    fs.rmSync("coverage", { recursive: true, force: true });
  }
  fs.mkdirSync("coverage/data", { recursive: true });
};
