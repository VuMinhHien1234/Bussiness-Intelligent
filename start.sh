#!/bin/bash
# start.sh — Khởi động toàn bộ VNRetail BI System với 1 lệnh
#
# Usage:
#   ./start.sh          → ETL đầy đủ + mở UI
#   ./start.sh --no-etl → Bỏ qua ETL, chỉ mở UI (khi data đã có sẵn trong DB)
#
set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

SKIP_ETL=false
if [[ "$1" == "--no-etl" ]]; then
  SKIP_ETL=true
fi

# ── Banner ─────────────────────────────────────────────────────────────────
echo ""
echo "╔══════════════════════════════════════════════╗"
echo "║        VNRetail BI System — Khởi động       ║"
echo "╚══════════════════════════════════════════════╝"
echo ""

# ── Kiểm tra Docker ────────────────────────────────────────────────────────
if ! command -v docker &>/dev/null; then
  echo "❌ Lỗi: Docker chưa được cài đặt."
  echo "   Tải tại: https://www.docker.com/products/docker-desktop"
  exit 1
fi

if ! docker info &>/dev/null; then
  echo "❌ Lỗi: Docker chưa chạy. Hãy mở Docker Desktop trước."
  exit 1
fi

# ── Bước 1: PostgreSQL ─────────────────────────────────────────────────────
echo "▶ [1/3] Khởi động PostgreSQL (Docker)..."
docker compose up -d postgres

echo -n "      Chờ PostgreSQL sẵn sàng"
until docker exec bi_postgres pg_isready -U bi_user -d bi_db -q 2>/dev/null; do
  echo -n "."
  sleep 1
done
echo " ✓"

# ── Bước 2: ETL ────────────────────────────────────────────────────────────
if [ "$SKIP_ETL" = true ]; then
  echo ""
  echo "⏭  [2/3] Bỏ qua ETL (--no-etl)"
else
  echo ""
  echo "▶ [2/3] Chạy ETL Pipeline (load data → DWH)..."
  echo "         (Lần đầu có thể mất 1-2 phút)"
  echo ""

  # Tạo schema + tables
  docker exec -i bi_postgres psql -U bi_user -d bi_db < etl/sql-marketing.sql

  # Cài Python packages nếu thiếu
  python3 -m pip install pandas psycopg2-binary python-dotenv openpyxl streamlit \
    --quiet --break-system-packages 2>/dev/null \
    || python3 -m pip install pandas psycopg2-binary python-dotenv openpyxl streamlit --quiet

  # Cập nhật thời tiết
  echo "      → Cập nhật dữ liệu thời tiết..."
  python3 etl/fetch_weather.py 2>/dev/null \
    || echo "      (!) API thời tiết không khả dụng — dùng file cache sẵn có."

  # Load data vào DWH
  echo "      → Nạp dữ liệu vào Data Warehouse..."
  python3 etl/main.py

  echo ""
  echo "      ✓ ETL hoàn thành!"
fi

# ── Bước 3: Streamlit UI ───────────────────────────────────────────────────
echo ""
echo "▶ [3/3] Khởi động giao diện web..."

# Cài streamlit nếu chưa có
if ! command -v streamlit &>/dev/null; then
  echo "      Cài đặt Streamlit..."
  python3 -m pip install streamlit --quiet --break-system-packages 2>/dev/null \
    || python3 -m pip install streamlit --quiet
fi

echo ""
echo "╔══════════════════════════════════════════════╗"
echo "║  ✅ Hệ thống sẵn sàng!                       ║"
echo "║                                              ║"
echo "║  🌐 Giao diện: http://localhost:8501          ║"
echo "║  🗄️  Database:  localhost:5434 / bi_db        ║"
echo "║  📊 Tableau:   Kết nối qua PostgreSQL         ║"
echo "║                                              ║"
echo "║  Nhấn Ctrl+C để dừng hệ thống               ║"
echo "╚══════════════════════════════════════════════╝"
echo ""

streamlit run app.py --server.port 8501 --browser.gatherUsageStats false
