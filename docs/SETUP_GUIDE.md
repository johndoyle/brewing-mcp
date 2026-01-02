# Brewing MCP - Setup Guide

This guide explains how to configure and run the MCP servers on macOS and Windows.

## Overview

The brewing-mcp servers use **environment variables** for configuration, not a `config.toml` file. Each server requires specific environment variables to be set before running.

## MCP Servers

### 1. BeerSmith MCP

**Purpose**: Access BeerSmith recipes, ingredients, and brewing calculations

**Environment Variables**:

| Variable | Required | Description | Example |
|----------|----------|-------------|---------|
| `BEERSMITH_PATH` | No* | Path to BeerSmith data folder | See OS-specific below |
| `BEERSMITH_BACKUP_PATH` | No | Path for backups (optional) | `~/Documents/BeerSmith3-backup` |

*Automatically detected on macOS/Linux/Windows if not set

### 2. Grocy MCP

**Purpose**: Manage inventory, stock, shopping lists, recipes, and chores

**Environment Variables**:

| Variable | Required | Description | Example |
|----------|----------|-------------|---------|
| `GROCY_URL` | Yes | Grocy server URL | `http://localhost:9283` |
| `GROCY_API_KEY` | Yes | Grocy API key | `abcd1234efgh5678` |

---

## macOS Setup

### BeerSmith MCP

BeerSmith on macOS stores data in:
```
~/Library/Application Support/BeerSmith3
```

**Configuration** (choose one):

#### Option 1: Use Auto-Detection (Recommended)
If BeerSmith 3 is installed in the default location, no configuration needed. The MCP will auto-detect it.

#### Option 2: Set Environment Variable
If using a non-standard location:

```bash
export BEERSMITH_PATH=~/Library/Application\ Support/BeerSmith3
```

### Grocy MCP

**Prerequisites**:
- Grocy server running locally or remotely
- API key from Grocy

**Get Your Grocy API Key**:
1. Open Grocy in your browser
2. Navigate to **Settings → Manage API keys**
3. Create or copy an existing API key

**Configuration**:

```bash
export GROCY_URL=http://localhost:9283
export GROCY_API_KEY=your-api-key-here
```

If your Grocy instance is on a different machine:
```bash
export GROCY_URL=http://192.168.1.100:9283
export GROCY_API_KEY=your-api-key-here
```

### Running on macOS

**Terminal Method** (Temporary - variables only set for this session):

```bash
cd /Users/john/Development/brewing-mcp

# Run BeerSmith MCP
uv run --package mcp-beersmith python -m mcp_beersmith

# Or run Grocy MCP (in another terminal)
export GROCY_URL=http://localhost:9283
export GROCY_API_KEY=your-api-key
uv run --package mcp-grocy python -m mcp_grocy
```

**Permanent Setup with Claude Desktop**:

Edit `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "beersmith": {
      "command": "uv",
      "args": [
        "run",
        "--directory",
        "/Users/john/Development/brewing-mcp",
        "--package",
        "mcp-beersmith",
        "python",
        "-m",
        "mcp_beersmith"
      ],
      "env": {
        "BEERSMITH_PATH": "~/Library/Application Support/BeerSmith3",
        "PYTHONWARNINGS": "ignore::DeprecationWarning"
      }
    },
    "grocy": {
      "command": "uv",
      "args": [
        "run",
        "--directory",
        "/Users/john/Development/brewing-mcp",
        "--package",
        "mcp-grocy",
        "python",
        "-m",
        "mcp_grocy"
      ],
      "env": {
        "GROCY_URL": "http://localhost:9283",
        "GROCY_API_KEY": "your-api-key-here",
        "PYTHONWARNINGS": "ignore::DeprecationWarning"
      }
    }
  }
}
```

Replace:
- `/Users/john/Development/brewing-mcp` with the actual path to your installation
- `your-api-key-here` with your actual Grocy API key
- `localhost:9283` with your Grocy server address if different

**Note**: `PYTHONWARNINGS` suppresses deprecation warnings that can interfere with the MCP protocol.

---

## Windows Setup

### BeerSmith MCP

BeerSmith on Windows typically stores data in one of:
```
C:\Users\YourUsername\Documents\BeerSmith3
C:\Users\YourUsername\AppData\Local\BeerSmith3
```

**Configuration** (choose one):

#### Option 1: Use Auto-Detection (Recommended)
If BeerSmith is installed in the default location, no configuration needed.

#### Option 2: Set Environment Variable
If using a non-standard location:

**PowerShell** (Temporary):
```powershell
$env:BEERSMITH_PATH = "C:\Users\YourUsername\Documents\BeerSmith3"
```

**PowerShell** (Permanent - Current User):
```powershell
[Environment]::SetEnvironmentVariable("BEERSMITH_PATH", "C:\Users\YourUsername\Documents\BeerSmith3", "User")
```

**Command Prompt** (Temporary):
```cmd
set BEERSMITH_PATH=C:\Users\YourUsername\Documents\BeerSmith3
```

**Command Prompt** (Permanent - Current User):
```cmd
setx BEERSMITH_PATH "C:\Users\YourUsername\Documents\BeerSmith3"
```

**GUI Method**:
1. Press `Win + X` → Select "System"
2. Click "Advanced system settings"
3. Click "Environment Variables..."
4. Under "User variables", click "New..."
5. Variable name: `BEERSMITH_PATH`
6. Variable value: `C:\Users\YourUsername\Documents\BeerSmith3`
7. Click OK twice, then restart any open applications

### Grocy MCP

**Prerequisites**:
- Grocy server running locally or remotely
- API key from Grocy

**Get Your Grocy API Key**:
1. Open Grocy in your browser
2. Navigate to **Settings → Manage API keys**
3. Create or copy an existing API key

**Configuration**:

**PowerShell** (Temporary):
```powershell
$env:GROCY_URL = "http://localhost:9283"
$env:GROCY_API_KEY = "your-api-key-here"
```

**PowerShell** (Permanent - Current User):
```powershell
[Environment]::SetEnvironmentVariable("GROCY_URL", "http://localhost:9283", "User")
[Environment]::SetEnvironmentVariable("GROCY_API_KEY", "your-api-key-here", "User")
```

**Command Prompt** (Temporary):
```cmd
set GROCY_URL=http://localhost:9283
set GROCY_API_KEY=your-api-key-here
```

**Command Prompt** (Permanent - Current User):
```cmd
setx GROCY_URL "http://localhost:9283"
setx GROCY_API_KEY "your-api-key-here"
```

**GUI Method**:
1. Press `Win + X` → Select "System"
2. Click "Advanced system settings"
3. Click "Environment Variables..."
4. Under "User variables", click "New..." (twice)
5. First variable:
   - Name: `GROCY_URL`
   - Value: `http://localhost:9283`
6. Second variable:
   - Name: `GROCY_API_KEY`
   - Value: `your-api-key-here`
7. Click OK three times, then restart any open applications

### Running on Windows

**PowerShell**:

```powershell
cd C:\path\to\brewing-mcp

# Set environment variables (if using temporary method)
$env:GROCY_URL = "http://localhost:9283"
$env:GROCY_API_KEY = "your-api-key"

# Run BeerSmith MCP
uv run --package mcp-beersmith python -m mcp_beersmith

# Or run Grocy MCP (in another PowerShell window)
$env:GROCY_URL = "http://localhost:9283"
$env:GROCY_API_KEY = "your-api-key"
uv run --package mcp-grocy python -m mcp_grocy
```

**Command Prompt**:

```cmd
cd C:\path\to\brewing-mcp

REM Set environment variables (if using temporary method)
set GROCY_URL=http://localhost:9283
set GROCY_API_KEY=your-api-key

REM Run BeerSmith MCP
uv run --package mcp-beersmith python -m mcp_beersmith

REM Or run Grocy MCP (in another Command Prompt)
set GROCY_URL=http://localhost:9283
set GROCY_API_KEY=your-api-key
uv run --package mcp-grocy python -m mcp_grocy
```

**Permanent Setup with Claude Desktop**:

Edit `%APPDATA%\Claude\claude_desktop_config.json` (usually at `C:\Users\YourUsername\AppData\Roaming\Claude\claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "beersmith": {
      "command": "uv",
      "args": [
        "run",
        "--directory",
        "C:\\path\\to\\brewing-mcp",
        "--package",
        "mcp-beersmith",
        "python",
        "-m",
        "mcp_beersmith"
      ],
      "env": {
        "BEERSMITH_PATH": "C:\\Users\\YourUsername\\Documents\\BeerSmith3",
        "PYTHONWARNINGS": "ignore::DeprecationWarning"
      }
    },
    "grocy": {
      "command": "uv",
      "args": [
        "run",
        "--directory",
        "C:\\path\\to\\brewing-mcp",
        "--package",
        "mcp-grocy",
        "python",
        "-m",
        "mcp_grocy"
      ],
      "env": {
        "GROCY_URL": "http://localhost:9283",
        "GROCY_API_KEY": "your-api-key-here",
        "PYTHONWARNINGS": "ignore::DeprecationWarning"
      }
    }
  }
}
```

Replace:
- `C:\path\to\brewing-mcp` with actual path to your installation
- `C:\Users\YourUsername\Documents\BeerSmith3` with your BeerSmith path
- `your-api-key-here` with your actual Grocy API key
- `localhost:9283` with your Grocy server address if different

**Note**: Use double backslashes (`\\`) in JSON for Windows paths

---

## Troubleshooting

### BeerSmith MCP

**Error: "BEERSMITH_PATH environment variable not set and no default BeerSmith installation found"**

Solution:
1. Check that BeerSmith is installed in a standard location
2. If using a custom location, set `BEERSMITH_PATH` environment variable explicitly
3. Ensure the path exists: `ls -la ~/Library/Application\ Support/BeerSmith3` (macOS) or check Windows path

**Error: "Unable to read BeerSmith data files"**

Solution:
1. Verify the path is correct and readable
2. Ensure BeerSmith data files are not corrupted
3. Try specifying `BEERSMITH_BACKUP_PATH` to use a backup

### Grocy MCP

**Error: "GROCY_URL environment variable not set"**

Solution:
1. Ensure `GROCY_URL` is set before running the server
2. Format should be: `http://hostname:port` (e.g., `http://localhost:9283`)
3. Don't include trailing slash

**Error: "GROCY_API_KEY environment variable not set"**

Solution:
1. Get your API key from Grocy: Settings → Manage API keys
2. Set the environment variable before running the server
3. Verify the key is copied exactly without spaces

**Error: "Connection refused" or "Cannot connect to Grocy"**

Solution:
1. Verify Grocy server is running and accessible
2. Check the URL is correct (e.g., `http://192.168.1.100:9283`)
3. Ensure network connectivity between your machine and Grocy server
4. Check Grocy firewall settings if remote

---

## Environment Variables Quick Reference

### macOS/Linux Export

Add to `~/.bashrc`, `~/.zshrc`, or `~/.bash_profile`:

```bash
export GROCY_URL="http://localhost:9283"
export GROCY_API_KEY="your-api-key"
export BEERSMITH_PATH="~/Library/Application Support/BeerSmith3"  # Optional
```

Then run:
```bash
source ~/.zshrc  # or ~/.bashrc or ~/.bash_profile
```

### Windows PowerShell Profile

Create/edit `$PROFILE`:

```powershell
$env:GROCY_URL = "http://localhost:9283"
$env:GROCY_API_KEY = "your-api-key"
$env:BEERSMITH_PATH = "C:\Users\YourUsername\Documents\BeerSmith3"  # Optional
```

### Using .env File (Python)

Create a `.env` file in the brewing-mcp directory:

```env
GROCY_URL=http://localhost:9283
GROCY_API_KEY=your-api-key
BEERSMITH_PATH=/path/to/beersmith
```

Then load before running:

**macOS/Linux**:
```bash
source .env
uv run --package mcp-grocy python -m mcp_grocy
```

**Windows PowerShell**:
```powershell
Get-Content .env | ForEach-Object {
  $name, $value = $_.split('=')
  New-Item -Path env:$name -Value $value -Force | Out-Null
}
uv run --package mcp-grocy python -m mcp_grocy
```

---

## Next Steps

1. [Set up environment variables for your OS](#macOS-setup) or [Windows](#windows-setup)
2. Configure Claude Desktop with the MCP servers
3. Test by running: `uv run --package mcp-beersmith python -m mcp_beersmith`
4. Restart Claude Desktop to load the MCPs
5. Start using the brewing tools in Claude!
