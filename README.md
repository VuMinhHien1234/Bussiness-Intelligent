# VNRetail — Hệ thống Business Intelligence

Dự án BI hoàn chỉnh: tích hợp **3 nguồn dữ liệu** (file Excel bán hàng, CSV quảng cáo Facebook, REST API thời tiết Open-Meteo) vào kho dữ liệu PostgreSQL theo mô hình **star schema / fact constellation**, vận hành qua pipeline ETL tự động, trực quan hóa trên **Tableau Desktop** với 5 dashboard tương tác.

Nghiên cứu trường hợp: dữ liệu mô phỏng tập đoàn VNRetail (FMCG), giai đoạn 2021–2025.

---

## Kiến trúc tổng thể

```
data/vnretail_data.xlsx       ┐
data/fb_ads_spend.csv         ├─→ app.py (Streamlit UI)
etl/fetch_weather.py (API)    ┘        │
                                       ▼
                              run_etl.sh
                                       │
                              ┌────────▼────────┐
                              │  PostgreSQL 15   │
                              │  (Docker :5434)  │
                              │                  │
                              │  schema staging  │  ← dữ liệu thô TEXT
                              │  schema dw       │  ← star schema sạch
                              └────────┬─────────┘
                                       │
                              Tableau Desktop
                              (5 dashboards)
```

### Schema DW — Star Schema

| Bảng | Loại | Số dòng | Mô tả |
|---|---|---|---|
| fact_marketing_sales | Fact | 14,981 | Doanh thu, chi phí, lợi nhuận, funnel |
| fact_ad_spend | Fact | 2,300 | Chi phí quảng cáo Facebook theo ngày × chiến dịch |
| fact_weather_daily | Fact | 5,478 | Thời tiết thực tế theo ngày × vùng (2021–2025) |
| dim_date | Dimension | 1,826 | Lịch đầy đủ: năm, quý, tháng |
| dim_product | Dimension | 40 | Sản phẩm với phân loại ngành hàng |
| dim_branch | Dimension | 9 | Chi nhánh với FK vùng địa lý |
| dim_region | Dimension | 3 | Miền Bắc / Miền Trung / Miền Nam |
| dim_channel | Dimension | 6 | Kênh bán hàng |
| dim_customer_segment | Dimension | 4 | Phân khúc khách hàng |
| dim_campaign | Dimension | 9 | Chiến dịch marketing |
| dim_department | Dimension | 6 | Phòng ban |
| dim_stage | Dimension | 5 | Funnel chuyển đổi |
| dim_machine | Dimension | 4 | Máy móc sản xuất |
| dim_information | Dimension | 4 | Loại thông tin khách hàng |

View `dw.v_sales_weather` join sẵn fact_marketing_sales + dim_branch + dim_product + fact_weather_daily — nguồn dữ liệu chính cho Tableau.

---

## Số liệu tổng quan

| Chỉ số | Giá trị |
|---|---|
| Tổng đơn hàng | 14,981 |
| Sản phẩm | 40 (7 ngành hàng) |
| Chi nhánh | 9 (3 vùng địa lý) |
| Kênh bán hàng | 6 |
| Giai đoạn | 2021–2025 |
| Tổng doanh thu | 99.1 tỷ VND |
| Tổng lợi nhuận | 22.9 tỷ VND |
| Biên lợi nhuận | 23.2% |

---

## Yêu cầu

- Docker Desktop (đang chạy)
- Python 3.10+
- Tableau Desktop 2024

---

## Khởi động — Hướng dẫn từng bước

### Bước 1 — Cài driver PostgreSQL cho Tableau (chỉ làm 1 lần duy nhất)

Tableau không tự kết nối được PostgreSQL, cần cài thêm driver:

1. Tải file `.jar` tại: **jdbc.postgresql.org/download**
2. Chạy lệnh sau để tạo thư mục và copy driver vào:
```bash
mkdir -p ~/Library/Tableau/Drivers
cp ~/Downloads/postgresql-*.jar ~/Library/Tableau/Drivers/
```
3. **Thoát hẳn Tableau (Cmd+Q) rồi mở lại** — bắt buộc, chỉ restart không đủ

---

### Bước 2 — Chạy hệ thống

Mở Terminal, chạy đúng 1 lệnh:

```bash
cd ~/Desktop/BI
./start.sh
```

Script tự làm tất cả:
1. Khởi động PostgreSQL trong Docker
2. Tạo schema + bảng
3. Cài thư viện Python nếu thiếu
4. Chạy ETL nạp cả 3 nguồn dữ liệu vào DW
5. Mở giao diện web tại `http://localhost:8501`

Chờ đến khi thấy dòng này là xong:
```
✅ Hệ thống sẵn sàng!
```

---

### Bước 3 — Kết nối Tableau với database

1. Mở **Tableau Desktop**
2. Màn hình Connect → chọn **PostgreSQL**
3. Điền thông số kết nối:

| Ô nhập | Giá trị |
|---|---|
| Server | `localhost` |
| Port | `5434` |
| Database | `bi_db` |
| Username | `bi_user` |
| Password | `bi_pass` |

4. Bấm **Sign In**
5. Bên trái chọn Schema → **dw**
6. Kéo bảng `fact_marketing_sales` vào vùng trắng ở giữa
7. Bấm **Sheet 1** ở dưới để bắt đầu làm dashboard

---

### Lần sau chạy lại

```bash
./start.sh
```

Vào Tableau bấm **F5** — dữ liệu tự cập nhật, không cần kết nối lại.

> **Chỉ mở UI, không chạy ETL:** `./start.sh --no-etl`

---

### Kiểm tra nhanh nếu dữ liệu không hiện

```bash
docker exec bi_postgres psql -U bi_user -d bi_db \
  -c "SELECT COUNT(*) FROM dw.fact_marketing_sales;"
```

Kết quả phải là `14981`. Nếu khác → chạy lại `./start.sh`.

---

## Kết nối Tableau

| Thông số | Giá trị |
|---|---|
| Host | `localhost` |
| Port | `5434` |
| Database | `bi_db` |
| Username | `bi_user` |
| Password | `bi_pass` |
| Schema | `dw` |

> macOS cần driver PostgreSQL JDBC (file `.jar` ~1 MB) đặt tại `~/Library/Tableau/Drivers`. Tải tại jdbc.postgresql.org, thoát hẳn Tableau (Cmd+Q) rồi mở lại.

---

## Cấu trúc thư mục

```
BI/
├── app.py                          # Streamlit UI: upload → validate → ETL
├── run_etl.sh                      # Chạy toàn bộ pipeline bằng 1 lệnh
├── docker-compose.yml              # PostgreSQL 15, port 5434
├── .env                            # Cấu hình kết nối DB và tên bảng
│
├── etl/
│   ├── sql-marketing.sql           # DDL: tạo staging + dw (idempotent)
│   ├── py-marketing.py             # ETL Python: 3 nguồn → staging → dw
│   └── fetch_weather.py            # Gọi Open-Meteo API → weather_daily.csv
│
├── data/
│   ├── vnretail_data.xlsx          # Nguồn 1: bán hàng (14,981 đơn, 37 cột)
│   ├── fb_ads_spend.csv            # Nguồn 2: chi phí quảng cáo Facebook
│   ├── weather_daily.csv           # Nguồn 3: thời tiết 3 vùng × 5 năm
│   └── test_data_errors.xlsx       # File test validation (1,500 dòng, 40% lỗi)
│
└── docs/
    └── VNRetail_BI_Report_Plain_EN.docx   # Báo cáo phân tích đầy đủ (tiếng Anh)
```

---

## Cập nhật dữ liệu

- **Thêm/sửa đơn hàng**: sửa `data/vnretail_data.xlsx` (giữ đúng 37 cột, ngày dạng `YYYY-MM-DD`) → chạy `./start.sh` → Refresh trong Tableau (F5).
- **Thêm chi quảng cáo**: thêm dòng vào `data/fb_ads_spend.csv` (ngày `dd/mm/yyyy`, campaign slug như `tet_promotion`).
- **Thời tiết**: tự cập nhật qua API mỗi lần chạy `./start.sh`.

---

## Xử lý sự cố

**`port is already allocated`**
```bash
# Đổi port trong docker-compose.yml (vế trái 5434:5432) và DB_PORT trong .env
```

**Tableau báo thiếu driver**
- Tải PostgreSQL JDBC `.jar` từ jdbc.postgresql.org
- Đặt vào `~/Library/Tableau/Drivers`
- Thoát hẳn Tableau (Cmd+Q), mở lại

**Không thấy dữ liệu mới trên dashboard**
```bash
# Kiểm tra ETL đã chạy chưa
docker exec bi_postgres psql -U bi_user -d bi_db \
  -c "SELECT COUNT(*) FROM dw.fact_marketing_sales;"
# Nếu OK → Refresh trong Tableau (F5)
```

---

## Kiểm tra nhanh kho dữ liệu

```bash
docker exec bi_postgres psql -U bi_user -d bi_db -c \
  "SELECT EXTRACT(YEAR FROM full_date) AS year,
          COUNT(*) AS orders,
          ROUND(SUM(revenue)/1e6, 1) AS revenue_b,
          ROUND(SUM(profit)/SUM(revenue)*100, 1) AS margin_pct
   FROM dw.fact_marketing_sales
   GROUP BY 1 ORDER BY 1;"
```
