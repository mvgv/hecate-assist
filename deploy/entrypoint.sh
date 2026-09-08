#!/bin/sh
set -e

medassist seed-db
medassist ingest

exec "$@"
