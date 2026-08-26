#!/usr/bin/env bash
set -uo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SITES_FILE="${SITES_FILE:-${ROOT_DIR}/sites.txt}"
OUT_DIR="${OUT_DIR:-${ROOT_DIR}/out}"
WORK_DIR="${WORK_DIR:-${ROOT_DIR}/work}"
PAGE_LIMIT="${PAGE_LIMIT:-20}"
SITE_SIZE_LIMIT_MIB="${SITE_SIZE_LIMIT_MIB:-10}"
RESOURCE_SIZE_LIMIT_MIB="${RESOURCE_SIZE_LIMIT_MIB:-1}"
SITE_TIMEOUT_MINUTES="${SITE_TIMEOUT_MINUTES:-2}"
SITE_HARD_LIMIT_MIB="${SITE_HARD_LIMIT_MIB:-12}"
RUN_STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
USER_AGENT="FreeTheDotYE-ArchiveBot/1.0 (+https://github.com/FreeTheDotYE/propaganda-machine)"

mkdir -p "${OUT_DIR}" "${WORK_DIR}"
MANIFEST="${OUT_DIR}/manifest.csv"
printf 'captured_at,site,queued_pages,archive,result,wget_exit_code,bytes,discovery\n' > "${MANIFEST}"

if [[ ! -f "${SITES_FILE}" ]]; then
  echo "missing sites file: ${SITES_FILE}" >&2
  exit 1
fi

archive_count=0
failure_count=0

while IFS= read -r raw_line || [[ -n "${raw_line}" ]]; do
  site="${raw_line%%#*}"
  site="$(printf '%s' "${site}" | sed -E 's/^[[:space:]]+|[[:space:]]+$//g')"
  [[ -z "${site}" ]] && continue

  case "${site}" in
    http://*.ye|https://*.ye|http://*.ye/*|https://*.ye/*) ;;
    *)
      echo "skipping non-.ye or malformed target: ${site}" >&2
      continue
      ;;
  esac

  slug="$(printf '%s' "${site}" | sed -E 's#^https?://##; s#[^A-Za-z0-9._-]+#-#g; s#^-+|-+$##g')"
  site_work="${WORK_DIR}/${slug}"
  urls_file="${site_work}/urls.txt"
  mkdir -p "${site_work}/download"

  discovery="full"
  if ! python3 "${ROOT_DIR}/scripts/discover.py" "${site}" "${PAGE_LIMIT}" "${urls_file}"; then
    echo "link discovery failed for ${site}; archiving the homepage only" >&2
    printf '%s\n' "${site}" > "${urls_file}"
    discovery="homepage-only"
  fi

  queued_pages="$(wc -l < "${urls_file}" | tr -d ' ')"
  effective_home="$(head -n 1 "${urls_file}")"
  host="$(printf '%s' "${effective_home}" | sed -E 's#^https?://([^/:]+).*#\1#')"
  warc_base="${OUT_DIR}/${slug}-${RUN_STAMP}"
  log_file="${site_work}/wget.log"

  echo "archiving ${site}: ${queued_pages} queued pages, same-host assets, ${SITE_SIZE_LIMIT_MIB} MiB quota"
  if timeout --kill-after=30s "${SITE_TIMEOUT_MINUTES}m" \
    wget \
      --input-file="${urls_file}" \
      --directory-prefix="${site_work}/download" \
      --warc-file="${warc_base}" \
      --warc-cdx \
      --warc-compression \
      --page-requisites \
      --delete-after \
      --domains="${host}" \
      --execute robots=off \
      --no-check-certificate \
      --timeout=10 \
      --tries=1 \
      --quota="${SITE_SIZE_LIMIT_MIB}m" \
      --max-filesize="${RESOURCE_SIZE_LIMIT_MIB}m" \
      --user-agent="${USER_AGENT}" \
      --no-verbose \
      --output-file="${log_file}"; then
    wget_exit=0
  else
    wget_exit=$?
  fi

  warc_file="${warc_base}.warc.gz"
  hard_limit_bytes=$((SITE_HARD_LIMIT_MIB * 1024 * 1024))
  if [[ -s "${warc_file}" ]] && (( $(stat -c '%s' "${warc_file}") > hard_limit_bytes )); then
    echo "discarding oversized WARC for ${site}; hard limit is ${SITE_HARD_LIMIT_MIB} MiB" >&2
    rm -f -- "${warc_file}" "${warc_base}.cdx"
    archive_name=""
    bytes=0
    result="failed-hard-size-limit"
    failure_count=$((failure_count + 1))
  elif [[ -s "${warc_file}" ]]; then
    archive_name="$(basename "${warc_file}")"
    bytes="$(stat -c '%s' "${warc_file}")"
    if [[ "${wget_exit}" -eq 0 ]]; then
      result="archived"
    else
      result="archived-with-wget-exit-${wget_exit}"
    fi
    archive_count=$((archive_count + 1))
  else
    archive_name=""
    bytes=0
    result="failed"
    failure_count=$((failure_count + 1))
  fi

  printf '%s,%s,%s,%s,%s,%s,%s,%s\n' \
    "${RUN_STAMP}" "${site}" "${queued_pages}" "${archive_name}" \
    "${result}" "${wget_exit}" "${bytes}" "${discovery}" >> "${MANIFEST}"
done < "${SITES_FILE}"

shopt -s nullglob
warc_files=("${OUT_DIR}"/*.warc.gz)
if (( ${#warc_files[@]} == 0 )); then
  echo "no WARC archives were created" >&2
  exit 1
fi

(
  cd "${OUT_DIR}"
  sha256sum ./*.warc.gz > SHA256SUMS
)

echo "created ${archive_count} WARC archives; ${failure_count} targets failed completely"
