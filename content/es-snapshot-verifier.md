Title: Secure Snapshot Verification in Elasticsearch with Minimal Privileges
Date: 2025-04-20
Author: Oliver Rivas
Category: DevSecOps
Tags: elasticsearch, snapshot, security, observability, prometheus, minimal-permissions
Slug: elasticsearch-secure-snapshot-verification
Summary: Learn how to securely verify Elasticsearch snapshots without using `manage_snapshot`, using a minimal API key, Prometheus-compatible script, and hardened monitoring practices. Includes a GitHub tools repo for automation.

# Es Snapshot Verifier

Verifying Elasticsearch snapshots typically requires broad `manage` permissions. This can be risky, especially if credentials are compromised. We can reduce the blast radius by defining a minimal role that grants only the specific actions necessary to verify snapshots without allowing deletions or alterations.

In some environments, using external monitoring systems like Datadog or Prometheus may not be feasible. Whether due to air-gapped infrastructure, compliance restrictions, or footprint concerns, having a hardened custom script with minimal privileges can be a reliable fallback.

To improve portability and maintainability, this article now references code and configuration files hosted in the [elasticsearch-tools GitHub repository](https://github.com/rivassec/elasticsearch-tools). This structure allows future updates to the tools without requiring edits to the article.

## Minimal Elasticsearch Role

Here is a role that avoids using `manage_snapshot` to reduce exposure. This ensures a compromised API key cannot delete or tamper with existing backups:

[View full role definition](https://github.com/rivassec/elasticsearch-tools/blob/main/roles/snapshot_repo_readonly.json)
```json
{
  "snapshot_repo_readonly": {
    "cluster": [
      "cluster:admin/repository/get",
      "cluster:admin/repository/verify",
      "cluster:admin/snapshot/get",
      "cluster:admin/snapshot/status"
    ],
    "indices": [],
    "run_as": [],
    "metadata": {},
    "transient_metadata": {
      "enabled": true
    }
  }
}
```

## API Key Generation

To generate an API key restricted to this role, use the following `curl` command. This allows access only to the approved cluster actions with a defined expiration period:

```bash
curl -u elastic:${ELASTICPASS} -X POST "localhost:9200/_security/api_key" \
  -H "Content-Type: application/json" \
  -d @elasticsearch-tools/roles/snapshot_repo_readonly.json
```

## Snapshot Verifier Script

This API key can be used with a lightweight shell script that verifies the repository and emits Prometheus-compatible metrics. The script is secure by design and includes input validation, safe temporary file handling, and minimal permissions.

[View the script](https://github.com/rivassec/elasticsearch-tools/blob/main/scripts/verify_snapshot.sh)
```bash
#!/bin/bash

########################################################################
# Hardened Snapshot Monitor for Elasticsearch
# Purpose: Verify an Elasticsearch snapshot repository and expose
# Prometheus-style metrics securely.
########################################################################

set -euo pipefail

: "${ES_HOST:="http://localhost:9200"}"
: "${REPO_NAME:?Missing REPO_NAME}"
: "${API_KEY_FILE:="/etc/elasticsearch/readonly-api-key"}"
: "${PROM_FILE:="/var/lib/node_exporter/textfile_collector/es_snapshot.prom"}"

if [[ ! -f "$API_KEY_FILE" ]]; then
  echo "[FATAL] API key file not found: $API_KEY_FILE" >&2
  exit 2
fi

if [[ $(stat -c "%a" "$API_KEY_FILE") -gt 600 ]]; then
  echo "[FATAL] API key file permissions too permissive (should be 600 or less)" >&2
  exit 3
fi

API_KEY=$(<"$API_KEY_FILE")
TMP_PROM_FILE=$(mktemp)
safe_repo=safe_repo="${REPO_NAME//[^a-zA-Z0-9_]/_}"
timestamp=$(date +%s)

response=$(curl -fsSL --retry 3 --retry-delay 2 \
  -H "Authorization: ApiKey $API_KEY" \
  -H "Content-Type: application/json" \
  -X POST "$ES_HOST/_snapshot/$REPO_NAME/_verify" || true)

if jq -e '.nodes | length > 0' <<<"$response" >/dev/null 2>&1; then
  result=1
  status="ok"
else
  result=0
  status="failed"
fi

{
  echo "# HELP es_snapshot_repository_verified Success status of snapshot verification"
  echo "# TYPE es_snapshot_repository_verified gauge"
  echo "es_snapshot_repository_verified{repo=\"$safe_repo\"} $result"
  echo "# HELP es_snapshot_repository_verified_at Unix timestamp of last check"
  echo "# TYPE es_snapshot_repository_verified_at gauge"
  echo "es_snapshot_repository_verified_at{repo=\"$safe_repo\"} $timestamp"
} > "$TMP_PROM_FILE"

mv "$TMP_PROM_FILE" "$PROM_FILE"
logger -t es-snapshot-monitor "[INFO] Verification $status for '$REPO_NAME' (code=$result)"

exit 0
```

## Cron Example

A cron job can be configured to run the script regularly:

[View example cron wrapper](https://github.com/rivassec/elasticsearch-tools/blob/main/examples/example_cronjob.sh)
```bash
#!/bin/bash

# Note: For production use, place this logic directly into a cron job or systemd timer.
#       This script is just an example for demonstration and testing.

# Fail fast on error
set -euo pipefail

# === Configuration ===
export REPO_NAME="my_backup_repo"
export ES_HOST="http://localhost:9200"
export API_KEY_FILE="/etc/elasticsearch/readonly-api-key"
export PROM_FILE="/var/lib/node_exporter/textfile_collector/es_snapshot_${REPO_NAME}.prom"

# === Invoke snapshot verification script ===
/opt/elasticsearch-tools/tools/snapshot-verifier/verify_snapshot.sh
```

## Usage Instructions

To install, configure, and run the snapshot verification system, follow the documentation in the repository:
[View usage guide](https://github.com/rivassec/elasticsearch-tools/blob/main/docs/USAGE.md)

This structure is ideal for environments with limited connectivity or strict compliance rules. It keeps the verification logic reproducible, auditable, and safe from privilege escalation risks. Updates to the tooling can be managed independently of the article, improving long-term maintainability.
