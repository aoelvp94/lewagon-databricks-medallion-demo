#!/usr/bin/env bash
# Measure dbt parse / compile on teaching vs scale projects.
# Never prints env secret values — only timings and node counts.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
# Non-secret placeholders so profiles.yml env_var() resolves during parse.
# Override with real values + BENCH_COMPILE=1 to time compile.
export DATABRICKS_HOST="${DATABRICKS_HOST:-dbc-placeholder.cloud.databricks.com}"
export DATABRICKS_HTTP_PATH="${DATABRICKS_HTTP_PATH:-/sql/1.0/warehouses/placeholder}"
export DATABRICKS_TOKEN="${DATABRICKS_TOKEN:-dapi_placeholder_not_a_real_token}"

OUT_DIR="${ROOT}/bench/results"
mkdir -p "${OUT_DIR}"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
RESULT="${OUT_DIR}/bench_${STAMP}.json"

DBT_BIN="${DBT_BIN:-dbt}"
PROJECT_TEACHING="${ROOT}/dags/dbt/lw_commerce"
PROJECT_SCALE="${ROOT}/dags/dbt/lw_commerce_scale"

# Compile hits the warehouse — only when BENCH_COMPILE=1
do_compile=0
if [[ "${BENCH_COMPILE:-0}" == "1" ]]; then
  do_compile=1
fi

time_cmd() {
  local label="$1"; shift
  local start end elapsed rc
  start=$(date +%s.%N)
  set +e
  "$@" >/tmp/dbt_bench_stdout.txt 2>/tmp/dbt_bench_stderr.txt
  rc=$?
  set -e
  end=$(date +%s.%N)
  elapsed=$(python3 -c "print(f'{float('${end}')-float('${start}'):.3f}')")
  if [[ $rc -eq 0 ]]; then
    echo "${label}: OK ${elapsed}s" >&2
    printf '%s' "${elapsed}"
  else
    echo "${label}: FAIL ${elapsed}s (see /tmp/dbt_bench_stderr.txt)" >&2
    printf '%s' "null"
  fi
}

echo "dbt binary: ${DBT_BIN}"
"${DBT_BIN}" --version || true
echo "compile enabled: ${do_compile} (values not shown)"

TEACH_PARSE=$(time_cmd "teaching parse" "${DBT_BIN}" parse --project-dir "${PROJECT_TEACHING}" --profiles-dir "${PROJECT_TEACHING}")
SCALE_PARSE=$(time_cmd "scale parse" "${DBT_BIN}" parse --project-dir "${PROJECT_SCALE}" --profiles-dir "${PROJECT_SCALE}")

TEACH_PARSE_V2="null"
SCALE_PARSE_V2="null"
if "${DBT_BIN}" parse --help 2>&1 | grep -q -- '--use-v2-parser'; then
  TEACH_PARSE_V2=$(time_cmd "teaching parse --use-v2-parser" "${DBT_BIN}" parse --use-v2-parser --project-dir "${PROJECT_TEACHING}" --profiles-dir "${PROJECT_TEACHING}")
  SCALE_PARSE_V2=$(time_cmd "scale parse --use-v2-parser" "${DBT_BIN}" parse --use-v2-parser --project-dir "${PROJECT_SCALE}" --profiles-dir "${PROJECT_SCALE}")
else
  echo "note: --use-v2-parser not available on this dbt binary (expected on Core 1.12+)"
fi

TEACH_COMPILE="null"
SCALE_COMPILE="null"
if [[ "${do_compile}" == "1" ]]; then
  TEACH_COMPILE=$(time_cmd "teaching compile" "${DBT_BIN}" compile --project-dir "${PROJECT_TEACHING}" --profiles-dir "${PROJECT_TEACHING}")
  SCALE_COMPILE=$(time_cmd "scale compile" "${DBT_BIN}" compile --project-dir "${PROJECT_SCALE}" --profiles-dir "${PROJECT_SCALE}")
else
  echo "skipping compile: set BENCH_COMPILE=1 with real DATABRICKS_* to enable (values not logged)"
fi

TEACH_NODES=$(find "${PROJECT_TEACHING}/models" -name '*.sql' 2>/dev/null | wc -l | tr -d ' ')
SCALE_NODES=$(find "${PROJECT_SCALE}/models" -name '*.sql' 2>/dev/null | wc -l | tr -d ' ')

python3 - "${RESULT}" "${STAMP}" "${DBT_BIN}" "${TEACH_NODES}" "${SCALE_NODES}" \
  "${TEACH_PARSE}" "${SCALE_PARSE}" "${TEACH_PARSE_V2}" "${SCALE_PARSE_V2}" \
  "${TEACH_COMPILE}" "${SCALE_COMPILE}" "${do_compile}" <<'PY'
import json, subprocess, sys
out, stamp, dbt_bin, teach_n, scale_n = sys.argv[1:6]
tp, sp, tp2, sp2, tc, sc, do_c = sys.argv[6:13]

def num(x):
    if x in (None, "", "null"):
        return None
    return float(x)

try:
    ver = subprocess.check_output([dbt_bin, "--version"], text=True, stderr=subprocess.STDOUT)
except Exception as e:
    ver = str(e)

payload = {
    "stamp_utc": stamp,
    "dbt_bin": dbt_bin,
    "dbt_version_text": ver.strip(),
    "teaching_sql_models": int(teach_n),
    "scale_sql_models": int(scale_n),
    "seconds": {
        "teaching_parse": num(tp),
        "scale_parse": num(sp),
        "teaching_parse_use_v2_parser": num(tp2),
        "scale_parse_use_v2_parser": num(sp2),
        "teaching_compile": num(tc),
        "scale_compile": num(sc),
    },
    "compile_ran": do_c == "1",
}
with open(out, "w", encoding="utf-8") as f:
    json.dump(payload, f, indent=2)
    f.write("\n")
print(f"Wrote {out}")
print(json.dumps(payload, indent=2))
PY
