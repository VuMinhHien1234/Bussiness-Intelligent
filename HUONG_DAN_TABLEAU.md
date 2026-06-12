# Tableau — dựng từng biểu đồ y như trong báo cáo (bấm vào đâu, chọn gì)

Bản hướng dẫn cầm tay cho **Tableau Desktop trên macOS**, dựng lại 8 biểu đồ (Hình 1–8) trong `Bao_Cao_Du_An_BI_Marketing.docx`. (Bản Power BI tương ứng: `HUONG_DAN_POWERBI.md`.)

Các vùng màn hình dùng suốt bài:

- **Data pane** (cột trái): danh sách trường, nhóm theo bảng — nơi *kéo* trường ra.
- **Columns / Rows** (2 thanh trên cùng): nơi *thả* trường — Columns = trục ngang, Rows = trục dọc.
- **Marks card** (giữa trái): đổi kiểu biểu đồ (Bar/Line...), chứa các ô **Color / Size / Label / Tooltip**.
- **Pill** = viên thuốc xuất hiện khi thả trường vào Columns/Rows. Right-click pill để đổi cách tính.

---

## BƯỚC 0 — Chuẩn bị một lần

### 0.1. Kết nối

1. Chạy dữ liệu trước: Terminal → `cd ~/Desktop/BI && ./run_etl.sh`.
2. Mở Tableau → cột trái **Connect → To a Server → PostgreSQL**.
3. Điền: Server `localhost` — Port `5434` — Database `bi_db` — Authentication: Username and Password — Username `bi_user` — Password `bi_pass` → **Sign In**.
4. (Lỗi "driver not installed": tải file `.jar` từ jdbc.postgresql.org, bỏ vào `~/Library/Tableau/Drivers`, Cmd+Q Tableau mở lại. File phải ~1 MB.)

### 0.2. Dựng model (trang Data Source)

1. Kéo **fact_marketing_sales** từ danh sách bảng (cột trái) vào canvas trắng.
2. Kéo tiếp từng bảng thả **cạnh** fact: `dim_date`, `dim_product`, `dim_branch`, `dim_region`(thả cạnh dim_branch), `dim_campaign`, `dim_channel`, `dim_stage`, `dim_customer_segment`. Tableau tự nối qua cột trùng tên — bấm vào đường nối kiểm tra đúng cặp (vd `full_date = full_date`).
3. **Bỏ qua** các bảng `staging.*` và `vinamilk/masan_case_xlsx`.
4. Đặt tên data source (góc trên trái, double-click): `Sales DW`.

### 0.3. Thêm 2 data source phụ

- **Ads**: menu **Data → New Data Source** → PostgreSQL (thông số như trên) → kéo `fact_ad_spend` + `dim_date` + `dim_campaign` vào canvas → đặt tên `Ads`.
- **Thời tiết**: Data → New Data Source → kéo mỗi view **v_sales_weather** → đặt tên `Sales+Weather`. (View này đã join sẵn bán hàng + vùng + nhiệt độ — không cần nối gì.)

Chuyển qua lại giữa các nguồn: bấm tên nguồn ở đầu Data pane trong mỗi worksheet.

### 0.4. Cách tạo Calculated Field (dùng nhiều lần)

Menu **Analysis → Create Calculated Field…** (hoặc bấm ▾ cạnh ô tìm kiếm trong Data pane → Create Calculated Field). Gõ tên ở ô trên, công thức ở ô dưới → **OK**. Trường mới xuất hiện trong Data pane, kéo dùng như trường thường.

---

## Hình 1 — Doanh thu theo tháng (đường)

*Data source: Sales DW*

1. Sheet mới (icon ➕ dưới cùng).
2. Kéo `Year Month` (bảng dim_date) → thả vào **Columns**.
3. Kéo `Revenue` (fact) → thả vào **Rows** (tự thành SUM(Revenue)).
4. Marks card: đổi **Automatic → Line**.
5. Format tiền: right-click pill `SUM(Revenue)` → **Format…** → khung trái mục **Numbers → Currency (Custom)** → Decimal places `0`, Display Units `Thousands (K)`.
6. Double-click tên "Sheet 1" dưới cùng → đặt `H1 Doanh thu theo tháng`.

## Hình 2 — Doanh thu TB/đơn: hè vs đông theo ngành (cột nhóm)

*Data source: Sales DW*

1. Tạo Calculated Field tên `Mùa`:
   ```
   IF [Month] >= 5 AND [Month] <= 8 THEN "Hè (T5-8)"
   ELSEIF [Month] >= 11 OR [Month] <= 2 THEN "Đông (T11-2)"
   END
   ```
   (`[Month]` là trường của dim_date — gõ `[Mo` Tableau tự gợi ý.)
2. Kéo `Category Name` (dim_product) → **Columns**; kéo `Mùa` → **Columns**, thả bên phải pill trước.
3. Kéo `Revenue` → **Rows** → right-click pill → **Measure (Sum) → Average**.
4. Kéo `Mùa` lần nữa → thả vào ô **Color** trên Marks card.
5. Lọc bỏ Null: kéo `Mùa` → khung **Filters** → tick 2 mùa, bỏ Null → OK.

## Hình 3 — Nhiệt độ vs doanh thu Kem Miền Bắc (cột + đường, 2 trục)

*Data source: Sales+Weather (view v_sales_weather)*

1. Tạo Calculated Field `Year Month W`: `LEFT(STR([Full Date]), 7)`.
2. Kéo `Year Month W` → **Columns**.
3. Kéo `Revenue` → **Rows**. Kéo tiếp `Temp Mean` → **Rows**, thả bên phải (thành 2 biểu đồ chồng dọc) → right-click pill `Temp Mean` → **Measure → Average**.
4. Right-click pill `AVG(Temp Mean)` → **Dual Axis** (2 biểu đồ nhập làm 1, 2 trục 2 bên).
5. Marks card giờ có 3 thẻ: chọn thẻ **SUM(Revenue)** → đổi thành **Bar**; thẻ **AVG(Temp Mean)** → **Line**.
6. Kéo `Category Name` → **Filters** → tick `Kem`. Kéo `Region Name` → **Filters** → tick `Miền Bắc`.

## Hình 4 — Doanh thu / 1 đồng quảng cáo theo chiến dịch (thanh ngang, trộn 2 nguồn)

1. Sheet mới, đang đứng ở nguồn **Sales DW**: kéo `Campaign Name` (dim_campaign) → **Rows**.
2. Data pane → bấm chuyển sang nguồn **Ads** → thấy icon **mắt xích** cạnh trường `Campaign Name` — bấm cho nó **đỏ/cam (active)**: hai nguồn được link theo chiến dịch (data blending).
3. Quay về nguồn **Sales DW**, tạo Calculated Field `Rev per Ad`:
   ```
   SUM([Revenue]) / SUM([Ads].[Spend])
   ```
   (Gõ `[Ads].` Tableau tự gợi ý trường của nguồn phụ.)
4. Kéo `Rev per Ad` → **Columns**.
5. Sort: bấm icon **sort giảm dần** trên toolbar (hình cột + mũi tên xuống).
6. Hiện số: kéo `Rev per Ad` lần nữa → thả vào ô **Label** trên Marks card.

## Hình 5 — Phễu marketing (thanh ngang)

*Data source: Sales DW*

1. Kéo `Stage Name` (dim_stage) → **Rows**.
2. Kéo `fact_marketing_sales (Count)` (trường tự sinh, cuối nhóm fact trong Data pane) → **Columns**.
3. Sửa thứ tự: right-click pill `Stage Name` → **Sort…** → Sort By: **Field**, Sort Order: **Ascending**, Field Name: `Stage Order`, Aggregation: Minimum → đóng hộp thoại.

## Hình 6 — Cơ cấu theo kênh và theo vùng (2 sheet thanh)

*Data source: Sales DW*

- Sheet `H6a Theo kênh`: `Channel Name` → **Rows**; `Revenue` → **Columns**; bấm icon sort giảm dần.
- Sheet `H6b Theo vùng`: `Region Name` (dim_region) → **Rows**; `Revenue` → **Columns**.

## Hình 7 — Tỷ trọng 4 cấu phần chi phí trên doanh thu (4 đường theo năm)

*Data source: Sales DW*

1. Tạo 4 Calculated Field:
   ```
   % Nguyên liệu : SUM([Raw Material Cost]) / SUM([Revenue])
   % Nhân công   : SUM([Labor Cost]) / SUM([Revenue])
   % Logistics   : SUM([Logistics Cost]) / SUM([Revenue])
   % Marketing   : SUM([Marketing Cost]) / SUM([Revenue])
   ```
2. Kéo `Year` (dim_date) → **Columns** → nếu pill màu xanh lá liên tục, right-click → **Discrete**.
3. Kéo `% Nguyên liệu` → **Rows**. Kéo `% Nhân công` thả **đè lên trục dọc** của biểu đồ vừa tạo (xuất hiện 2 thước kẻ xanh thì thả) — Tableau tự gộp thành Measure Values. Kéo tiếp 2 trường % còn lại thả vào khung **Measure Values** (hiện ra dưới Marks).
4. Kéo `Measure Names` (đầu Data pane) → ô **Color**.
5. Marks: chọn **Line**. Format %: right-click từng pill trong Measure Values → Format → Numbers → Percentage, 1 decimal.

## Hình 8 — CPA (cột) và CPC (đường) theo tháng

*Data source: Ads*

1. Tạo 2 Calculated Field: `CPA` = `SUM([Spend]) / SUM([Conversions])` và `CPC` = `SUM([Spend]) / SUM([Clicks])`.
2. Kéo `Month` (dim_date) → **Columns** (để Discrete — pill xanh dương).
3. Kéo `CPA` → **Rows**; kéo `CPC` → **Rows** bên phải → right-click pill `CPC` → **Dual Axis**.
4. Marks: thẻ `CPA` → **Bar**; thẻ `CPC` → **Line**.

---

## Ghép dashboard

1. Bấm icon **New Dashboard** (cạnh icon New Worksheet, dưới cùng).
2. Khung trái liệt kê các sheet — kéo từng sheet vào canvas. Gợi ý chia 5 dashboard theo Bảng 7 của báo cáo: Tổng quan (H1, H6a, H6b) / Phễu & kênh (H5, H6a) / Chiến dịch & quảng cáo (H4, H8) / Thời tiết & mùa vụ (H3, H2) / Vùng & vận hành (H6b + sheet tự thêm).
3. **Filter năm dùng chung**: vào 1 sheet → right-click `Year` (dim_date) → **Show Filter**; trong dashboard, bấm ▾ trên filter → **Apply to Worksheets → All Using This Data Source**.
4. Size dashboard: khung trái dưới cùng → **Size → Automatic**.

## Lưu và xuất

- Lưu workbook: **File → Save** (`.twb`).
- Gửi người khác xem (kèm dữ liệu): **File → Export Packaged Workbook** (`.twbx`) — mở được bằng Tableau Reader miễn phí.
- Lấy ảnh chèn Word: vào dashboard → **Dashboard → Export Image…**.

## Khi biểu đồ "không ra"

- Trống trơn → kiểm tra đang đứng đúng data source (đầu Data pane), và ETL đã chạy.
- Hình 4 ra số khổng lồ/sai → quên bật **mắt xích** link Campaign Name ở nguồn Ads (bước quan trọng nhất của blending).
- Tỷ lệ % thành 2.300% → pill đang Sum thay vì công thức — phải dùng Calculated Field như hướng dẫn, không kéo thẳng cột gốc.
- Trục tháng nhảy lung tung → pill `Month`/`Year Month` phải **Discrete** (màu xanh dương), right-click → Discrete.
- Phễu sai thứ tự → bước Sort theo `Stage Order` (Hình 5, bước 3).
