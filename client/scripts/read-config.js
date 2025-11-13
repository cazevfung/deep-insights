/**
 * Read config.yaml and export frontend server configuration.
 * This script reads the config.yaml file and extracts server configuration
 * for use in vite.config.ts.
 */
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import yaml from 'js-yaml';

// Get __dirname equivalent in ES modules
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Path to config.yaml (two levels up from client/scripts/)
const configPath = path.resolve(__dirname, '../../config.yaml');

let config = null;

try {
  const configContent = fs.readFileSync(configPath, 'utf8');
  config = yaml.load(configContent);
} catch (error) {
  console.warn(`Warning: Could not read config.yaml from ${configPath}`);
  console.warn(`Using default configuration. Error: ${error.message}`);
  config = null;
}

// Extract server configuration with defaults
const envBackendPort = process.env.BACKEND_PORT_OVERRIDE;
const envFrontendPort = process.env.FRONTEND_PORT_OVERRIDE;

// Try to read port info from file (written by install_dependencies.py)
let portInfoFile = null;
try {
  const portInfoPath = path.resolve(__dirname, '../../.server-ports.json');
  if (fs.existsSync(portInfoPath)) {
    const portInfoContent = fs.readFileSync(portInfoPath, 'utf8');
    portInfoFile = JSON.parse(portInfoContent);
    console.log(`[Vite Config] Read port info from file: backend=${portInfoFile.backendPort}, frontend=${portInfoFile.frontendPort}`);
  } else {
    console.log(`[Vite Config] Port info file not found at ${portInfoPath}, using defaults`);
  }
} catch (error) {
  console.warn(`[Vite Config] Error reading port info file: ${error.message}`);
}

const backendPort = (() => {
  // Priority: environment variable > port info file > config.yaml > default
  if (envBackendPort) {
    const parsed = Number.parseInt(envBackendPort, 10);
    if (!Number.isNaN(parsed) && parsed > 0) {
      console.log(`[Vite Config] Using backend port from env: ${parsed}`);
      return parsed;
    }
  }
  if (portInfoFile?.backendPort) {
    const parsed = Number.parseInt(portInfoFile.backendPort, 10);
    if (!Number.isNaN(parsed) && parsed > 0) {
      console.log(`[Vite Config] Using backend port from file: ${parsed}`);
      return parsed;
    }
  }
  const defaultPort = config?.servers?.backend?.port || 3001;
  console.log(`[Vite Config] Using backend port from config/default: ${defaultPort}`);
  return defaultPort;
})();

const frontendHost = process.env.FRONTEND_HOST_OVERRIDE || config?.servers?.frontend?.host || '0.0.0.0';

const frontendPort = (() => {
  // Priority: environment variable > port info file > config.yaml > default
  if (envFrontendPort) {
    const parsed = Number.parseInt(envFrontendPort, 10);
    if (!Number.isNaN(parsed) && parsed > 0) {
      return parsed;
    }
  }
  if (portInfoFile?.frontendPort) {
    const parsed = Number.parseInt(portInfoFile.frontendPort, 10);
    if (!Number.isNaN(parsed) && parsed > 0) {
      return parsed;
    }
  }
  return config?.servers?.frontend?.port || 3000;
})();
const proxyTimeout = config?.servers?.frontend?.proxy_timeout || 10000;

// Export configuration
export default {
  frontendHost,
  frontendPort,
  backendPort,
  proxyTarget: `http://localhost:${backendPort}`,
  proxyTimeout,
};

