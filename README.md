# Hệ thống BI phân tích dữ liệu Marketing đa nguồn

Dự án Business Intelligence hoàn chỉnh: hợp nhất **3 nguồn dữ liệu** (bán hàng Excel, quảng cáo Facebook CSV, thời tiết thực tế CSV) vào kho dữ liệu PostgreSQL theo mô hình **star schema / fact constellation**, vận hành bằng pipeline ETL tự động, trực quan hóa trên **Tableau / Power BI**. Nghiên cứu trường hợp: dữ liệu marketing mô phỏng của Tập đoàn Masan, giai đoạn 2021–2025.

## Kiến trúc

```
masan_case.xlsx (3.746 đơn hàng)      ┐
fb_ads_spend.csv (1.831 ngày x CD)    ├─→ run_etl.sh ─→ PostgreSQL (Docker, cổng 5434)
weather_daily.csv (5.478 ngày x vùng) ┘        │            ├─ schema staging: 3 bảng thô
                                               │            └─ schema dw: 11 dim + 3 fact + view
                                               └─→ Tableau / Power BI (kéo thả dashboard)
```

- **Staging**: dữ liệu nguyên trạng dạng TEXT, nạp kiểu truncate-reload.
- **DW**: 11 dimension dùng chung (date, region, branch, product, stage, channel, campaign, segment, department, machine, information) + 3 fact (`fact_marketing_sales`, `fact_ad_spend`, `fact_weather_daily`) + view `v_sales_weather` join sẵn cho dashboard.
- **ETL** (`py-marketing.py`): parse ngày đa định dạng, map tên chiến dịch giữa 2 hệ thống, log số dòng bị loại theo lý do, nạp upsert (chạy lại bao nhiêu lần cũng an toàn).

## Yêu cầu

- Docker Desktop (đang chạy)
- Python 3 (macOS có sẵn; thư viện tự cài khi chạy script)
- Tableau Desktop hoặc Power BI Desktop (để xem dashboard)

## Chạy hệ thống

```bash
cd ~/Desktop/BI
./run_etl.sh
```

Script tự làm 4 việc: khởi động PostgreSQL trong Docker → dựng schema từ `sql-marketing.sql` → cài thư viện Python → chạy ETL nạp cả 3 nguồn. Khi thấy `ETL hoàn thành!` là dữ liệu sẵn sàng.

Lập lịch chạy tự động 9h sáng hằng ngày (tùy chọn):

```bash
EDITOR=nano crontab -e
# thêm dòng:
0 9 * * * cd ~/Desktop/BI && ./run_etl.sh >> etl.log 2>&1
```

## Kết nối công cụ BI

| Thông số | Giá trị |
|---|---|
| Host / Port | `localhost` / `5434` |
| Database | `bi_db` |
| User / Password | `bi_user` / `bi_pass` |
| Schema phân tích | `dw` |

Tableau trên macOS cần driver PostgreSQL JDBC (file `.jar`) đặt tại `~/Library/Tableau/Drivers`. Chi tiết cách dựng từng biểu đồ: xem `HUONG_DAN_DASHBOARD.md`.

## Cấu trúc thư mục

| File | Vai trò |
|---|---|
| `masan_case.xlsx` | Nguồn 1 — bán hàng (3.746 dòng, 2021–2025, 37 cột) |
| `fb_ads_spend.csv` | Nguồn 2 — chi quảng cáo Facebook theo ngày × chiến dịch |
| `weather_daily.csv` | Nguồn 3 — nhiệt độ/mưa thực tế 3 vùng (Hà Nội, Đà Nẵng, TP.HCM) |
| `docker-compose.yml` | PostgreSQL 15, cổng 5434, volume `pgdata` |
| `sql-marketing.sql` | Dựng staging + DW (11 dim, 3 fact, view, index) |
| `py-marketing.py` | ETL 3 nguồn: staging → làm sạch → DW |
| `run_etl.sh` | Chạy toàn bộ pipeline bằng 1 lệnh |
| `.env` | Cấu hình kết nối và tên bảng (đổi ở đây, không sửa code) |
| `fetch_weather.py` | Tạo/cập nhật `weather_daily.csv` (xóa file cũ rồi chạy để lấy thêm ngày mới) |
| `add_2025_data.py` | (đã dùng, 1 lần) sinh dữ liệu 2025 |
| `add_2021_2022_data.py` | (đã dùng, 1 lần) sinh dữ liệu lịch sử 2021–2022 |
| `adjust_sales_by_weather.py` | (đã dùng, 1 lần) hiệu chỉnh mùa vụ theo nhiệt độ thật — có khóa chống chạy lại |
| `pbi-marketing.pbix` | Dashboard Power BI (đổi cổng sang 5434 để dùng với kho mới) |
| `Bao_Cao_Du_An_BI_Marketing.docx` | Báo cáo dự án đầy đủ (27 trang, 9 chương) |
| `HUONG_DAN_DASHBOARD.md` | Hướng dẫn kéo thả Tableau + dùng Power BI |
| `masan_case_backup_*.xlsx` | Các bản backup dữ liệu trước mỗi lần biến đổi |

## Cập nhật dữ liệu

- **Thêm/sửa đơn hàng**: sửa trực tiếp `masan_case.xlsx` (đúng 37 cột, ngày dạng `YYYY-MM-DD`) → chạy `./run_etl.sh` → F5 trong Tableau.
- **Thêm chi quảng cáo**: thêm dòng vào `fb_ads_spend.csv` (ngày `dd/mm/yyyy`, campaign dạng slug như `tet_promotion`).
- **Thời tiết ngày mới**: `rm weather_daily.csv && ./run_etl.sh` (tự tải lại).

## Sự cố thường gặp

- **`port is already allocated` / `address already in use`**: cổng bị chiếm — đổi cổng trong `docker-compose.yml` (vế trái của `5434:5432`) và `DB_PORT` trong `.env` cho khớp.
- **`pip: command not found`**: script đã dùng `python3 -m pip`; nếu vẫn lỗi, cài Python từ python.org.
- **Tableau báo thiếu driver**: tải PostgreSQL JDBC `.jar` từ jdbc.postgresql.org, bỏ vào `~/Library/Tableau/Drivers`, thoát hẳn Tableau (Cmd+Q) mở lại. File phải nặng ~1 MB — nếu chỉ vài KB là tải hỏng.
- **Không thấy dữ liệu mới trên dashboard**: kiểm tra ETL đã chạy lại chưa (`docker exec bi_postgres psql -U bi_user -d bi_db -c "SELECT COUNT(*) FROM dw.fact_marketing_sales;"`), rồi Refresh (F5) trong Tableau.

## Kiểm tra nhanh kho dữ liệu

```bash
docker exec bi_postgres psql -U bi_user -d bi_db -c \
  "SELECT EXTRACT(YEAR FROM full_date) AS nam, COUNT(*), ROUND(SUM(revenue)) AS doanh_thu
   FROM dw.fact_marketing_sales GROUP BY 1 ORDER BY 1;"
```
