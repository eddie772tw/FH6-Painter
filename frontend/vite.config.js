import { defineConfig } from "vite";
import { execSync } from "child_process";

const host = process.env.TAURI_DEV_HOST;

let gitCommit = "unknown";
let gitBranch = "unknown";

try {
  gitBranch = execSync("git rev-parse --abbrev-ref HEAD").toString().trim();
  try {
    gitCommit = execSync("git describe --tags --exact-match HEAD", { stdio: 'pipe' }).toString().trim();
  } catch (e) {
    gitCommit = execSync("git rev-parse --short HEAD").toString().trim();
  }
  
  try {
    const status = execSync("git status --porcelain -uno").toString().trim();
    if (status.length > 0) {
      const changedFiles = status.split("\n").map(line => line.trim());
      const hasRealChanges = changedFiles.some(line => {
        const filePath = line.substring(2).trim();
        return !filePath.endsWith("Cargo.lock") && !filePath.endsWith("package-lock.json");
      });
      if (hasRealChanges) {
        gitCommit = "post-" + gitCommit;
      }
    }
  } catch (e) {
    // Ignore error checking status
  }
} catch (e) {
  console.warn("Could not retrieve git information.");
}

export default defineConfig({
  define: {
    __GIT_COMMIT__: JSON.stringify(gitCommit),
    __GIT_BRANCH__: JSON.stringify(gitBranch),
  },
  clearScreen: false,
  server: {
    port: 1420,
    strictPort: true,
    host: host || false,
    hmr: host
      ? {
          protocol: "ws",
          host,
          port: 1421,
        }
      : undefined,
    watch: {
      ignored: ["**/src-tauri/**"],
    },
  },
});
