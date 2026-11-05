#!/usr/bin/env bash
# Measure dbt parse / compile on teaching vs scale projects.
# Never prints env secret values — only timings and node counts.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT_DIR="${ROOT}/bench/results"
mkdir -p "${OUT_DIR}"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
RESULT="${OUT_DIR}/bench_${STAMP}.json"

DBT_BIN="${DBT_BIN:-dbt}"
PROJECT_TEACHING="${ROOT}/dags/dbt/lw_commerce"
PROJECT_SCALE="${ROOT}/dags/dbt/lw_commerce_scale"
PROFILES_DIR_TEACHING="${PROJECT_TEACHING}"
PROFILES_DIR_SCALE="${PROJECT_SCALE}"

have_creds=0
if [[ -n "${DATABRICKS_HOST:-}" && -n "${DATABRICKS_HTTP_PATH:-}" && -n "${DATABRICKS_TOKEN:-}" ]]; then
  have_creds=1
fi

time_cmd() {
  local label="$1"; shift
  local start end elapsed
  start=$(date +%s.%N)
  if "$@" >/tmp/dbt_bench_stdout.txt 2>/tmp/dbt_bench_stderr.txt; then
    end=$(date +%s.%N)
    elapsed=$(python3 -c "print(f'{float('${end}')-float('${start}'):.3f}')")
    echo "${label}: OK ${elapsed}s"
    printf '%s' "${elapsed}"
  else
    end=$(date +%s.%N)
    elapsed=$(python3 -c "print(f'{float('${end}')-float('${start}'):.3f}')")
    echo "${label}: FAIL ${elapsed}s (see /tmp/dbt_bench_stderr.txt)" >&2
    printf '%s' "null"
  fi
}

echo "dbt binary: ${DBT_BIN}"
"${DBT_BIN}" --version || true
echo "credentials present for compile: ${have_creds} (values not shown)"

json_escape() { python3 -c 'import json,sys; print(json.dumps(sys.stdin.read().rstrip("\n")))'; }

TEACH_PARSE=$(time_cmd "teaching parse" "${DBT_BIN}" parse --project-dir "${PROJECT_TEACHING}" --profiles-dir "${PROFILES_DIR_TEACHING}")
SCALE_PARSE=$(time_cmd "scale parse" "${DBT_BIN}" parse --project-dir "${PROJECT_SCALE}" --profiles-dir "${PROFILES_DIR_SCALE}")

TEACH_PARSE_V2="null"
SCALE_PARSE_V2="null"
if "${DBT_BIN}" parse --help 2>&1 | grep -q -- '--use-v2-parser'; then
  TEACH_PARSE_V2=$(time_cmd "teaching parse --use-v2-parser" "${DBT_BIN}" parse --use-v2-parser --project-dir "${PROJECT_TEACHING}" --profiles-dir "${PROFILES_DIR_TEACHING}")
  SCALE_PARSE_V2=$(time_cmd "scale parse --use-v2-parser" "${DBT_BIN}" parse --use-v2-parser --project-dir "${PROJECT_SCALE}" --profiles-dir "${PROFILES_DIR_SCALE}")
else
  echo "note: --use-v2-parser not available on this dbt binary (expected on Core 1.12+)"
fi

TEACH_COMPILE="null"
SCALE_COMPILE="null"
if [[ "${have_creds}" == "1" ]]; then
  TEACH_COMPILE=$(time_cmd "teaching compile" "${DBT_BIN}" compile --project-dir "${PROJECT_TEACHING}" --profiles-dir "${PROFILES_DIR_TEACHING}")
  SCALE_COMPILE=$(time_cmd "scale compile" "${DBT_BIN}" compile --project-dir "${PROJECT_SCALE}" --profiles-dir "${PROFILES_DIR_SCALE}")
else
  echo "skipping compile: set DATABRICKS_HOST / HTTP_PATH / TOKEN to enable (not logged)"
fi

TEACH_NODES=$(find "${PROJECT_TEACHING}/models" -name '*.sql' 2>/dev/null | wc -l | tr -d ' ')
SCALE_NODES=$(find "${PROJECT_SCALE}/models" -name '*.sql' 2>/dev/null | wc -l | tr -d ' ')
VERSION_JSON=$("${DBT_BIN}" --version 2>&1 | json_escape || echo '""')

cat > "${RESULT}" << JSON
{
  "stamp_utc": "${STAMP}",
  "dbt_bin": "${DBT_BIN}",
  "dbt_version_text": ${VERSION_JSON},
  "teaching_sql_models": ${TEACH_NODES},
  "scale_sql_models": ${SCALE_NODES},
  "seconds": {
    "teaching_parse": ${TEACH_PARSE},
    "scale_parse": ${SCALE_PARSE},
    "teaching_parse_use_v2_parser": ${TEACH_PARSE_V2},
    "scale_parse_use_v2_parser": ${SCALE_PARSE_V2},
    "teaching_compile": ${TEACH_COMPILE},
    "scale_compile": ${SCALE_COMPILE}
  },
  "compile_ran": $([[ "${have_creds}" == "1" ]] && echo true || echo false)
}
JSON

echo "Wrote ${RESULT}"
cat "${RESULT}"
