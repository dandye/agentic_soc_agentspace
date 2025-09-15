# Environment Variable Improvement Plan

## Executive Summary
This document outlines a comprehensive plan to improve environment variable management in the Agentic SOC AgentSpace project. The plan addresses significant duplication, improves naming consistency, and introduces programmatic construction of derived values.

## Current Issues Identified

### 1. Significant Duplication
- `PROJECT_ID` = `AGENTSPACE_PROJECT_ID` = `CHRONICLE_PROJECT_ID` (all "secops-demo-env")
- `PROJECT_NUMBER` = `AGENTSPACE_PROJECT_NUMBER` (both "813924125873")
- `LOCATION` = `GOOGLE_CLOUD_LOCATION` (both "us-central1")
- `AGENT_ENGINE_RESOURCE_NAME` = `AGENT_ENGINE_RESOURCE` (identical paths)

### 2. Constructable Paths
- `DATASTORE_PATH` hardcodes values that could be built from other vars
- `AGENT_ENGINE_RESOURCE_NAME` duplicates information already in other vars
- `STAGING_BUCKET` includes "gs://" prefix unnecessarily

### 3. Missing/Undocumented Variables
- `SECOPS_SA_PATH` used in main.py but missing from .env.example
- `AGENTSPACE_DATA_STORE_ID` in .env but not documented

### 4. Inconsistent Naming
- Mix of general (`PROJECT_ID`) and service-specific (`AGENTSPACE_PROJECT_ID`) names

## Implementation Plan

### Phase 1: Core Configuration Consolidation

#### Define base variables once:
- Keep `PROJECT_ID` as the single source of truth for Google Cloud project
- Keep `PROJECT_NUMBER` as the single source for project number
- Keep `LOCATION` as the standard region variable
- Add `STAGING_BUCKET_NAME` (without gs:// prefix)

#### Remove duplicates:
- Remove `AGENTSPACE_PROJECT_ID` (use `PROJECT_ID`)
- Remove `AGENTSPACE_PROJECT_NUMBER` (use `PROJECT_NUMBER`)
- Remove `GOOGLE_CLOUD_LOCATION` (use `LOCATION`)
- Remove `CHRONICLE_PROJECT_ID` (use `PROJECT_ID` unless different)
- Remove `AGENT_ENGINE_RESOURCE` (duplicate of AGENT_ENGINE_RESOURCE_NAME)

### Phase 2: Construct Derived Values in Code

#### Update main.py:
```python
# Construct staging bucket with prefix
STAGING_BUCKET = f"gs://{STAGING_BUCKET_NAME}"

# Use PROJECT_ID for Chronicle if same project
CHRONICLE_PROJECT_ID = os.environ.get("CHRONICLE_PROJECT_ID", PROJECT_ID)

# Construct agent engine resource name
if REASONING_ENGINE:
    AGENT_ENGINE_RESOURCE_NAME = f"projects/{PROJECT_NUMBER}/locations/{LOCATION}/reasoningEngines/{REASONING_ENGINE}"
```

#### Update manage_agentspace.py:
```python
# Use base variables
PROJECT_ID = self.env_vars["PROJECT_ID"]
PROJECT_NUMBER = self.env_vars["PROJECT_NUMBER"]

# Construct DATASTORE_PATH programmatically
DATASTORE_PATH = f"projects/{PROJECT_NUMBER}/locations/global/collections/default_collection/dataStores/{AGENTSPACE_DATA_STORE_ID}"
```

#### Update test_agent_engine.py:
```python
# Construct resource name from components
AGENT_ENGINE_RESOURCE_NAME = f"projects/{PROJECT_NUMBER}/locations/{LOCATION}/reasoningEngines/{REASONING_ENGINE}"
```

### Phase 3: Reorganize .env.example Structure

```bash
# ============================================
# CORE GOOGLE CLOUD CONFIGURATION
# ============================================
PROJECT_ID=your-project-id
PROJECT_NUMBER=123456789012
LOCATION=us-central1
STAGING_BUCKET_NAME=your-staging-bucket  # Without gs:// prefix
GOOGLE_API_KEY=your-google-api-key

# ============================================
# SECURITY OPERATIONS
# ============================================

# Chronicle SIEM Configuration
CHRONICLE_CUSTOMER_ID=01234567-abcd-4321-1234-0123456789ab
# Optional: Override if Chronicle is in different project
# CHRONICLE_PROJECT_ID=different-project-id
CHRONICLE_REGION=us
SECOPS_SERVICE_ACCOUNT_PATH=/path/to/service-account.json

# SOAR Platform Configuration
SOAR_URL=https://YOURS.siemplify-soar.com:443
SOAR_APP_KEY=your-soar-api-key

# Google Threat Intelligence (VirusTotal)
VT_APIKEY=your-virustotal-api-key

# ============================================
# VERTEX AI AGENT ENGINE
# ============================================
# Only the ID is needed; full path will be constructed
REASONING_ENGINE=8293875693058523136

# ============================================
# AGENTSPACE CONFIGURATION
# ============================================
AGENTSPACE_APP_ID=agentic-soc-agentspace-app_1757549640237
AGENTSPACE_AGENT_ID=9239948638551901607  # Optional: Set after agent creation
AGENTSPACE_DATA_STORE_ID=agentic-soc-ai-runbooks-datastore_1757549407776
AGENTSPACE_COLLECTION=default_collection  # Optional: Defaults to default_collection
AGENTSPACE_ASSISTANT=default_assistant    # Optional: Defaults to default_assistant

# ============================================
# OAUTH CONFIGURATION (Optional)
# ============================================
OAUTH_AUTH_ID=your-auth-id
OAUTH_CLIENT_ID=your-client-id.apps.googleusercontent.com
OAUTH_CLIENT_SECRET=your-client-secret
```

### Phase 4: Add Validation & Helper Scripts

#### Create installation_scripts/env_utils.py:
```python
import os
from typing import Dict, Optional, List
from pathlib import Path

class EnvManager:
    """Centralized environment variable management."""
    
    REQUIRED_VARS = [
        'PROJECT_ID', 'PROJECT_NUMBER', 'LOCATION', 
        'STAGING_BUCKET_NAME', 'GOOGLE_API_KEY'
    ]
    
    DEPRECATED_VARS = {
        'AGENTSPACE_PROJECT_ID': 'PROJECT_ID',
        'AGENTSPACE_PROJECT_NUMBER': 'PROJECT_NUMBER',
        'GOOGLE_CLOUD_LOCATION': 'LOCATION',
        'STAGING_BUCKET': 'STAGING_BUCKET_NAME',
        'AGENT_ENGINE_RESOURCE': 'AGENT_ENGINE_RESOURCE_NAME'
    }
    
    def __init__(self, env_file: Optional[Path] = None):
        self.env_vars = self._load_env(env_file)
        self._check_deprecated()
        self._validate_required()
    
    def get_staging_bucket(self) -> str:
        """Construct full staging bucket path."""
        bucket_name = self.env_vars['STAGING_BUCKET_NAME']
        if bucket_name.startswith('gs://'):
            return bucket_name
        return f"gs://{bucket_name}"
    
    def get_datastore_path(self) -> str:
        """Construct full datastore path."""
        return (f"projects/{self.env_vars['PROJECT_NUMBER']}/locations/global/"
                f"collections/{self.env_vars.get('AGENTSPACE_COLLECTION', 'default_collection')}/"
                f"dataStores/{self.env_vars['AGENTSPACE_DATA_STORE_ID']}")
    
    def get_agent_engine_resource(self) -> Optional[str]:
        """Construct agent engine resource name."""
        if reasoning_engine := self.env_vars.get('REASONING_ENGINE'):
            return (f"projects/{self.env_vars['PROJECT_NUMBER']}/"
                   f"locations/{self.env_vars['LOCATION']}/"
                   f"reasoningEngines/{reasoning_engine}")
        return None
    
    def _check_deprecated(self):
        """Check for deprecated variables and warn."""
        for old, new in self.DEPRECATED_VARS.items():
            if old in self.env_vars:
                print(f"⚠️  Warning: '{old}' is deprecated. Use '{new}' instead.")
                if new not in self.env_vars:
                    self.env_vars[new] = self.env_vars[old]
```

### Phase 5: Migration Support

#### Create installation_scripts/migrate_env.py:
```python
#!/usr/bin/env python3
"""Migrate .env file to new format."""

import sys
from pathlib import Path
import shutil
from datetime import datetime

def migrate_env_file(env_path: Path):
    """Migrate .env file to new format."""
    
    # Backup original
    backup_path = env_path.with_suffix(f'.env.backup.{datetime.now():%Y%m%d_%H%M%S}')
    shutil.copy2(env_path, backup_path)
    print(f"✓ Created backup: {backup_path}")
    
    # Read current env
    with open(env_path) as f:
        lines = f.readlines()
    
    # Apply transformations
    new_lines = []
    replacements = {
        'AGENTSPACE_PROJECT_ID': 'PROJECT_ID',
        'AGENTSPACE_PROJECT_NUMBER': 'PROJECT_NUMBER',
        'GOOGLE_CLOUD_LOCATION': 'LOCATION',
        'AGENT_ENGINE_RESOURCE=': '# AGENT_ENGINE_RESOURCE= # Deprecated - constructed automatically\n#',
    }
    
    for line in lines:
        modified = False
        for old, new in replacements.items():
            if line.startswith(f"{old}="):
                value = line.split('=', 1)[1]
                new_lines.append(f"# {line}")  # Keep old as comment
                new_lines.append(f"{new}={value}")
                modified = True
                break
        
        if not modified:
            new_lines.append(line)
    
    # Write new env
    with open(env_path, 'w') as f:
        f.writelines(new_lines)
    
    print(f"✓ Migrated {env_path}")
    print(f"  Old file backed up to: {backup_path}")

if __name__ == "__main__":
    env_file = Path(".env") if len(sys.argv) < 2 else Path(sys.argv[1])
    if env_file.exists():
        migrate_env_file(env_file)
    else:
        print(f"❌ File not found: {env_file}")
```

## Benefits

### Quantitative Improvements
- **~40% reduction** in environment variables (from ~25 to ~15 core variables)
- **Zero duplication** of project/location information
- **3 constructed paths** instead of hardcoded values

### Qualitative Improvements
- **Clearer naming:** Variables organized by service/scope
- **Easier maintenance:** Single source of truth for each value
- **Better documentation:** Grouped, well-commented structure
- **Type safety:** Validation and construction functions
- **Backwards compatibility:** Smooth migration path for existing deployments
- **Reduced errors:** Automatic path construction prevents typos

## Implementation Timeline

1. **Week 1:** Implement env_utils.py and migration script
2. **Week 2:** Update main.py, test_agent_engine.py with new structure
3. **Week 3:** Update manage_agentspace.py and other management scripts
4. **Week 4:** Update documentation and .env.example
5. **Week 5:** Testing and rollout with backwards compatibility

## Risk Mitigation

- **Backup Strategy:** All migrations create timestamped backups
- **Compatibility Layer:** Support old variable names with deprecation warnings
- **Phased Rollout:** Update scripts incrementally with fallback logic
- **Testing:** Comprehensive tests for all path construction functions
- **Documentation:** Clear migration guide for existing users

## Success Metrics

- All duplicate variables eliminated
- All constructed paths working correctly
- Zero breaking changes for existing deployments
- Improved developer experience measured by:
  - Fewer environment-related support issues
  - Faster onboarding for new developers
  - Reduced configuration errors