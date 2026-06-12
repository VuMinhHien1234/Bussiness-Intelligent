#!/bin/bash
# run_etl.sh — chạy toàn bộ BI ETL pipeline (Docker + PostgreSQL + Python)
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "======================================"
echo "  BI ETL Pipeline"
echo "======================================"

# 1. Start PostgreSQL via Docker
echo ""
echo "[1/4] Starting PostgreSQL (Docker)..."
docker compose up -d postgres

echo "      Waiting for PostgreSQL to be ready..."
until docker exec bi_postgres pg_isready -U bi_user -d bi_db -q 2>/dev/null; do
  sleep 1
done
echo "      PostgreSQL is ready."

# 2. Run SQL setup (create schemas + tables)
echo ""
echo "[2/4] Creating schemas and tables..."
docker exec -i bi_postgres psql -U bi_user -d bi_db < sql-marketing.sql
echo "      Done."

# 3. Install Python dependencies
echo ""
echo "[3/4] Installing Python dependencies..."
python3 -m pip install pandas psycopg2-binary python-dotenv openpyxl --quiet --break-system-packages 2>/dev/null \
  || python3 -m pip install pandas psycopg2-binary python-dotenv openpyxl --quiet
echo "      Done."

# 4. Run ETL
echo ""
echo "[4/4] Running ETL (Excel + Ads CSV + Weather API -> staging -> DW)..."
# Tải thời tiết (nguồn 3) nếu chưa có
[ -f weather_daily.csv ] || python3 fetch_weather.py
python3 py-marketing.py

echo ""
echo "======================================"
echo "  ETL hoàn thành!"
echo "  Kết nối Power BI/Tableau: localhost:5434 / bi_db / schema dw"
echo "======================================"
