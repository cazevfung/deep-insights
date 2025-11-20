# Plan: Config-Driven Server Configuration

## Overview
Make all server ports and configurations consistent across different computers by reading from `config.yaml` via `core/config.py`.

## Current State Analysis

### Hardcoded Ports/Configs Found:
1. **Backend** (`backend/run_server.py`): Port 3001 hardcoded
2. **Frontend** (`client/vite.config.ts`): Port 3000 hardcoded, proxy target `http://localhost:3001` hardcoded
3. **CORS** (`backend/app/main.py`): Origins hardcoded to `localhost:3000` and `localhost:3001`
4. **scripts/install/install_dependencies.py**: Ports 3001 and 3000 hardcoded in multiple places
   - `stop_backend_server(port=3001)`
   - `check_backend_health(port=3001)`
   - `start_servers()` references to ports 3001 and 3000
5. **scripts/install/run_windows.bat**: Calls Python script (no hardcoded values, but depends on script)

### Existing Config Structure:
- `config.yaml` has a `web` section (port 5000) but it's not used by the FastAPI server
- `core/config.py` exists and can read config values
- Config already supports dot notation (`config.get('web.port')`)

## Proposed Solution

### 1. Extend `config.yaml` Structure

Add a new `servers` section to `config.yaml`:

```yaml
servers:
  backend:
    host: '0.0.0.0'  # or '127.0.0.1' for local-only
    port: 3001
    reload: true
    reload_dirs: ['backend/app']
    
  frontend:
    port: 3000
    proxy_timeout: 10000
    proxy_target: 'http://localhost:3001'  # Will be derived from backend.port
    
  cors:
    allowed_origins:
      - 'http://localhost:3000'
      - 'http://127.0.0.1:3000'
      - 'http://localhost:3001'
      - 'http://127.0.0.1:3001'
    # Or use wildcard pattern: ['http://localhost:*', 'http://127.0.0.1:*']
```

**Note**: The `web` section (port 5000) appears to be for a different Flask-based web interface, so we'll keep it separate.

### 2. Update `core/config.py`

Add helper methods for server configuration:

```python
def get_backend_config(self) -> dict:
    """Get backend server configuration."""
    return {
        'host': self.get('servers.backend.host', '0.0.0.0'),
        'port': self.get_int('servers.backend.port', 3001),
        'reload': self.get_bool('servers.backend.reload', True),
        'reload_dirs': self.get('servers.backend.reload_dirs', ['backend/app']),
    }

def get_frontend_config(self) -> dict:
    """Get frontend server configuration."""
    backend_port = self.get_int('servers.backend.port', 3001)
    return {
        'port': self.get_int('servers.frontend.port', 3000),
        'proxy_timeout': self.get_int('servers.frontend.proxy_timeout', 10000),
        'proxy_target': self.get('servers.frontend.proxy_target', f'http://localhost:{backend_port}'),
    }

def get_cors_config(self) -> dict:
    """Get CORS configuration."""
    backend_port = self.get_int('servers.backend.port', 3001)
    frontend_port = self.get_int('servers.frontend.port', 3000)
    
    # Build default origins if not specified
    default_origins = [
        f'http://localhost:{frontend_port}',
        f'http://127.0.0.1:{frontend_port}',
        f'http://localhost:{backend_port}',
        f'http://127.0.0.1:{backend_port}',
    ]
    
    return {
        'allowed_origins': self.get('servers.cors.allowed_origins', default_origins),
        'allow_credentials': self.get_bool('servers.cors.allow_credentials', True),
        'allow_methods': self.get('servers.cors.allow_methods', ['*']),
        'allow_headers': self.get('servers.cors.allow_headers', ['*']),
    }
```

### 3. Update `backend/run_server.py`

```python
from core.config import Config

config = Config()
backend_config = config.get_backend_config()

uvicorn.run(
    "app.main:app",
    host=backend_config['host'],
    port=backend_config['port'],
    reload=backend_config['reload'],
    reload_dirs=backend_config['reload_dirs'],
)
```

### 4. Update `backend/app/main.py`

```python
from core.config import Config

config = Config()
cors_config = config.get_cors_config()

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_config['allowed_origins'],
    allow_credentials=cors_config['allow_credentials'],
    allow_methods=cors_config['allow_methods'],
    allow_headers=cors_config['allow_headers'],
)
```

### 5. Update `client/vite.config.ts`

**Challenge**: Vite config is TypeScript/JavaScript, not Python. We need to read `config.yaml` from Node.js.

**Solution Options**:
- **Option A**: Use a Node.js script to read `config.yaml` and generate a config file
- **Option B**: Use environment variables (set by Python script or shell)
- **Option C**: Use a Vite plugin to read `config.yaml` at build time
- **Option D**: Create a small Node.js utility to read YAML and export config

**Recommended: Option D** - Create `client/scripts/read-config.js`:

```javascript
// Read config.yaml and export frontend config
const fs = require('fs');
const path = require('path');
const yaml = require('js-yaml'); // Add to package.json

const configPath = path.resolve(__dirname, '../../config.yaml');
const config = yaml.load(fs.readFileSync(configPath, 'utf8'));

const backendPort = config?.servers?.backend?.port || 3001;
const frontendPort = config?.servers?.frontend?.port || 3000;

module.exports = {
  frontendPort,
  backendPort,
  proxyTarget: `http://localhost:${backendPort}`,
  proxyTimeout: config?.servers?.frontend?.proxy_timeout || 10000,
};
```

Then in `vite.config.ts`:

```typescript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'
import serverConfig from './scripts/read-config'

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: serverConfig.frontendPort,
    proxy: {
      '/api': {
        target: serverConfig.proxyTarget,
        changeOrigin: true,
        timeout: serverConfig.proxyTimeout,
        proxyTimeout: serverConfig.proxyTimeout,
      },
      '/ws': {
        target: `ws://localhost:${serverConfig.backendPort}`,
        ws: true,
      },
    },
  },
})
```

**Alternative (Simpler)**: Use environment variables set by a wrapper script.

### 6. Update `scripts/install/install_dependencies.py`

Replace all hardcoded port references:

```python
from core.config import Config

config = Config()
backend_config = config.get_backend_config()
frontend_config = config.get_frontend_config()

# Replace hardcoded 3001 with:
backend_port = backend_config['port']
frontend_port = frontend_config['port']

# Update all functions:
def stop_backend_server(port=None):
    if port is None:
        port = backend_config['port']
    # ... rest of function

def check_backend_health(port=None, timeout=30):
    if port is None:
        port = backend_config['port']
    # ... rest of function

def start_servers(...):
    backend_url = f"http://localhost:{backend_port}"
    frontend_url = f"http://localhost:{frontend_port}"
    # ... rest of function
```

### 7. Update `scripts/install/run_windows.bat`

No changes needed - it just calls the Python script which will read from config.

## Implementation Steps

### Phase 1: Config Structure
1. Add `servers` section to `config.yaml` with default values
2. Add helper methods to `core/config.py` for server configs
3. Test config reading

### Phase 2: Backend Updates
1. Update `backend/run_server.py` to use config
2. Update `backend/app/main.py` CORS to use config
3. Test backend starts correctly

### Phase 3: Frontend Updates
1. Add `js-yaml` to `client/package.json`
2. Create `client/scripts/read-config.js`
3. Update `client/vite.config.ts` to use config
4. Test frontend starts correctly

### Phase 4: Install Script Updates
1. Update `scripts/install/install_dependencies.py` to use config
2. Test server startup with config
3. Test health checks with config

### Phase 5: Validation & Documentation
1. Test on different machines
2. Verify ports are consistent
3. Update documentation
4. Create example config files

## Benefits

1. **Consistency**: Same ports on all machines via single config file
2. **Flexibility**: Easy to change ports if conflicts occur
3. **Maintainability**: Single source of truth for server configuration
4. **Portability**: Config file can be version controlled (with sensitive data in `.env` or separate file)
5. **Documentation**: Config file serves as documentation of server settings

## Edge Cases to Consider

1. **Port Conflicts**: If a port is already in use, we could:
   - Add validation in `run_server.py` to check if port is available
   - Add auto-increment logic (not recommended - breaks consistency)
   - Provide clear error messages

2. **Missing Config**: Provide sensible defaults in code

3. **Invalid Config**: Validate config values (e.g., ports must be 1024-65535)

4. **Environment Variables Override**: Allow env vars to override config (for deployment):
   ```python
   port = int(os.getenv('BACKEND_PORT', config.get('servers.backend.port', 3001)))
   ```

5. **Development vs Production**: Could use different config files:
   - `config.yaml` (development)
   - `config.prod.yaml` (production)
   - Select via `CONFIG_FILE` environment variable

## Migration Path

1. Add new config section with current hardcoded values
2. Update code to read from config (with fallback to current values)
3. Test thoroughly
4. Remove hardcoded values
5. Update documentation

## Testing Checklist

- [ ] Backend starts on configured port
- [ ] Frontend starts on configured port
- [ ] Frontend proxy correctly targets backend
- [ ] CORS allows configured origins
- [ ] Health checks use correct ports
- [ ] Install script uses correct ports
- [ ] Works on different machines with same config
- [ ] Works with different ports in config
- [ ] Error handling for missing/invalid config

