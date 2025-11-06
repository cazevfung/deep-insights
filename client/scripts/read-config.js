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
const backendPort = config?.servers?.backend?.port || 3001;
const frontendHost = config?.servers?.frontend?.host || '0.0.0.0';
const frontendPort = config?.servers?.frontend?.port || 3000;
const proxyTimeout = config?.servers?.frontend?.proxy_timeout || 10000;

// Export configuration
export default {
  frontendHost,
  frontendPort,
  backendPort,
  proxyTarget: `http://localhost:${backendPort}`,
  proxyTimeout,
};

