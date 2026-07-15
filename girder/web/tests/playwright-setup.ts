import fs from "fs";
import { execSync } from "node:child_process";

import { PlaywrightTestConfig } from "@playwright/test";

const PORT = 5173;

function killStaleServer() {
  if (process.platform === "win32") {
    // Find PIDs on the port, then taskkill each. Suppress errors so missing matches don't throw.
    const netstatOut = execSync(`netstat -ano | findstr :${PORT}`, { encoding: "utf8" });
    const pids = new Set<string>();
    for (const line of netstatOut.split("\n")) {
      const m = line.match(/\s(\d+)\s*$/);
      if (m) pids.add(m[1]);
    }
    for (const pid of pids) {
      try {
        execSync(`taskkill /PID ${pid} /F`, { stdio: "ignore" });
      } catch {
        // Process may have already exited; ignore.
      }
    }
  } else {
    // linux. lsof returns non-zero (and prints nothing) when nothing's listening.
    try {
      const pids = execSync(`lsof -ti tcp:${PORT}`, { encoding: "utf8" }).trim();
      if (pids) {
        for (const pid of pids.split("\n").filter(Boolean)) {
          try {
            process.kill(Number(pid), "SIGTERM");
          } catch {
            // ignore
          }
        }
      }
    } catch {
      // lsof exited non-zero — nothing listening, nothing to do.
    }
  }
}

export default async (_config: PlaywrightTestConfig) => {
  killStaleServer();

  if (fs.existsSync("coverage")) {
    fs.rmSync("coverage", { recursive: true, force: true });
  }
  fs.mkdirSync("coverage/data", { recursive: true });
};
