#!/usr/bin/env bash
set -e

./scripts/run_ingest.sh
./scripts/run_api.sh
