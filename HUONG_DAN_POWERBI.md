# Power BI — dựng từng biểu đồ y như trong báo cáo (bấm vào đâu, chọn gì)

Hướng dẫn này dắt tay từng cú click trong **Power BI Desktop** để tạo lại 8 biểu đồ (Hình 1–8) trong `Bao_Cao_Du_An_BI_Marketing.docx`.

Trên màn hình Power BI có 3 khung bên phải, dùng suốt bài này:

- **Data** (danh sách bảng/trường) — nơi *kéo* trường ra.
- **Visualizations** (lưới icon biểu đồ + các ô X-axis / Y-axis / Legend / Values) — nơi *thả* trường vào.
- **Filters** — nơi lọc riêng từng biểu đồ.

---

## BƯỚC 0 — Chuẩn bị một lần (làm xong mới vẽ)

### 0.1. Nạp bảng

1. **Home → Get data → PostgreSQL database**.
2. Server: `localhost:5434` — Database: `bi_db` → OK. (Tab **Database**: user `bi_user`, pass `bi_pass`.)
3. Tick các bảng: `dw.fact_marketing_sales`, `dw.fact_ad_spend`, `dw.dim_date`, `dw.dim_campaign`, `dw.dim_channel`, `dw.dim_stage`, `dw.dim_product`, `dw.dim_branch`, `dw.dim_region`, `dw.dim_customer_segment`, `dw.v_sales_weather` → **Load**.

### 0.2. Kiểm tra quan hệ

Bấm icon **Model view** (cột trái, hình 3 ô vuông nối nhau). Phải có các đường nối:

- `fact_marketing_sales[full_date]` → `dim_date[full_date]`
- `fact_marketing_sales[campaign_name]` → `dim_campaign[campaign_name]` (tương tự channel, stage, product, branch, segment)
- `fact_ad_spend[full_date]` → `dim_date[full_date]`
- `fact_ad_spend[campaign_name]` → `dim_campaign[campaign_name]`
- `dim_branch[region_name]` → `dim_region[region_name]`

Thiếu đường nào: **kéo** tên cột từ bảng này **thả đè** lên cột cùng tên ở bảng kia.

### 0.3. Tạo bộ measure (công thức tính)

Về **Report view** (icon biểu đồ cột trái). Trong khung Data, **right-click bảng `fact_marketing_sales` → New measure**, dán từng dòng (mỗi lần một measure, Enter để lưu):

```
Doanh thu = SUM(fact_marketing_sales[revenue])
```
```
Margin % = DIVIDE(SUM(fact_marketing_sales[profit]), SUM(fact_marketing_sales[revenue]))
```
```
% Nguyên liệu = DIVIDE(SUM(fact_marketing_sales[raw_material_cost]), SUM(fact_marketing_sales[revenue]))
```
```
% Nhân công = DIVIDE(SUM(fact_marketing_sales[labor_cost]), SUM(fact_marketing_sales[revenue]))
```
```
% Logistics = DIVIDE(SUM(fact_marketing_sales[logistics_cost]), SUM(fact_marketing_sales[revenue]))
```
```
% Marketing = DIVIDE(SUM(fact_marketing_sales[marketing_cost]), SUM(fact_marketing_sales[revenue]))
```

Right-click bảng `fact_ad_spend` → New measure, tạo tiếp:

```
Rev per Ad = DIVIDE(SUM(fact_marketing_sales[revenue]), SUM(fact_ad_spend[spend]))
```
```
CPC = DIVIDE(SUM(fact_ad_spend[spend]), SUM(fact_ad_spend[clicks]))
```
```
CPA = DIVIDE(SUM(fact_ad_spend[spend]), SUM(fact_ad_spend[conversions]))
```

Định dạng %: click chọn measure `Margin %` trong khung Data → ribbon **Measure tools** → bấm nút **%** → làm tương tự cho 4 measure `% ...`.

### 0.4. Tạo cột "Mùa" (cho Hình 2)

Right-click bảng `dim_date` → **New column**:

```
Mùa = SWITCH(TRUE(),
    dim_date[month] >= 5 && dim_date[month] <= 8, "Hè (T5-8)",
    dim_date[month] >= 11 || dim_date[month] <= 2, "Đông (T11-2)",
    "Khác")
```

### 0.5. Sắp thứ tự cho phễu

1. Bấm icon **Table view** (cột trái, hình bảng) → chọn bảng `dim_stage` → click cột `stage_name`.
2. Ribbon **Column tools → Sort by column → stage_order**.

Xong bước 0. Mỗi biểu đồ dưới đây: bấm vùng trống trên canvas rồi làm theo.

---

## Hình 1 — Doanh thu theo tháng (đường)

1. Khung Visualizations, bấm icon **Line chart** (hàng 1).
2. Kéo `dim_date[year_month]` → ô **X-axis**.
3. Kéo measure `Doanh thu` → ô **Y-axis**.
4. Nếu trục lộn xộn: bấm **… (More options)** góc biểu đồ → **Sort axis → year_month → Sort ascending**.
5. Gọn số trục: chọn biểu đồ → khung Visualizations bấm icon **Format (cây cọ) → Y-axis → Display units: Thousands**.

## Hình 2 — Doanh thu TB/đơn: hè vs đông theo ngành (cột nhóm)

1. Icon **Clustered column chart**.
2. `dim_product[category_name]` → **X-axis**; `dim_date[Mùa]` → **Legend**.
3. Kéo `fact_marketing_sales[revenue]` (cột gốc, không phải measure) → **Y-axis**, rồi bấm **mũi tên ▾ trên field đó → Average**.
4. Loại nhóm "Khác": kéo `dim_date[Mùa]` vào **Filters on this visual** → tick chỉ "Hè (T5-8)" và "Đông (T11-2)".

## Hình 3 — Nhiệt độ vs doanh thu Kem Miền Bắc (cột + đường, 2 trục)

Dùng bảng `v_sales_weather` (đã join sẵn — không đụng các bảng khác):

1. Icon **Line and clustered column chart**.
2. Kéo `v_sales_weather[full_date]` → **X-axis**; nó tự thành hierarchy — bấm **▾ trên field → chọn Date** rồi ở Format → X-axis đổi Type: **Categorical**? Cách dễ hơn: right-click bảng `v_sales_weather` → New column: `YearMonth = FORMAT(v_sales_weather[full_date], "YYYY-MM")` rồi kéo `YearMonth` vào X-axis.
3. Kéo `v_sales_weather[revenue]` → **Column y-axis**.
4. Kéo `v_sales_weather[temp_mean]` → **Line y-axis**, bấm **▾ → Average**.
5. Khung **Filters on this visual**: kéo `category_name` vào → tick **Kem**; kéo `region_name` vào → tick **Miền Bắc**.

## Hình 4 — Doanh thu / 1 đồng quảng cáo theo chiến dịch (thanh ngang)

1. Icon **Clustered bar chart**.
2. `dim_campaign[campaign_name]` → **Y-axis**; measure `Rev per Ad` → **X-axis**.
3. **… → Sort axis → Rev per Ad → Sort descending**.
4. Hiện số trên thanh: **Format (cây cọ) → Data labels: On**.

(Measure này tự đúng vì cả 2 fact cùng nối vào `dim_campaign` — đó là lý do thiết kế conformed dimension.)

## Hình 5 — Phễu marketing

1. Icon **Funnel**.
2. `dim_stage[stage_name]` → **Category**.
3. `fact_marketing_sales[order_id]` → **Values**, bấm **▾ → Count**.
4. Thứ tự đúng nhờ bước 0.5; nếu vẫn lệch: **… → Sort axis → stage_name**.

## Hình 6 — Cơ cấu theo kênh và theo vùng (2 biểu đồ thanh)

Biểu đồ 1: icon **Clustered bar chart** → `dim_channel[channel_name]` → Y-axis; `Doanh thu` → X-axis; sort descending.

Biểu đồ 2: thêm **Clustered bar chart** thứ hai → `dim_region[region_name]` → Y-axis; `Doanh thu` → X-axis.

## Hình 7 — Tỷ trọng 4 cấu phần chi phí trên doanh thu (4 đường theo năm)

1. Icon **Line chart**.
2. `dim_date[year]` → **X-axis** (bấm ▾ trên field → chọn **year**, không lấy hierarchy; Format → X-axis → Type: **Categorical** để khỏi hiện 2,021.5).
3. Kéo lần lượt 4 measure `% Nguyên liệu`, `% Nhân công`, `% Logistics`, `% Marketing` → cùng ô **Y-axis** (xếp chồng thành 4 đường).
4. Nếu chưa format %, quay lại bước 0.3.

## Hình 8 — CPA (cột) và CPC (đường) theo tháng

1. Icon **Line and clustered column chart**.
2. `dim_date[month]` → **X-axis** (Format → X-axis → Type: Categorical).
3. Measure `CPA` → **Column y-axis**; measure `CPC` → **Line y-axis**.

Lưu ý: biểu đồ này chạy trên dữ liệu ads nên tháng ở đây đi qua quan hệ `fact_ad_spend → dim_date`.

---

## Ghép thành dashboard và bộ lọc chung

1. Mỗi trang (Page) trong Power BI là một dashboard — đặt tên tab dưới cùng theo 5 dashboard đề xuất trong báo cáo (Tổng quan / Phễu & kênh / Chiến dịch & quảng cáo / Thời tiết & mùa vụ / Vùng & vận hành), kéo các biểu đồ liên quan vào cùng trang.
2. Bộ lọc cho cả trang: kéo `dim_date[year]` vào **Filters on this page**, hoặc chèn **Slicer** (icon trong Visualizations) rồi kéo `year` vào — người xem tự bấm chọn năm.
3. Lưu file: **File → Save As** → đặt tên mới (vd `pbi-marketing-v2.pbix`) để giữ nguyên bản cũ.

## Khi số "không ra"

- Tất cả bằng 0/trống → kiểm tra đã Load bảng từ schema `dw` (không phải `staging`), và ETL đã chạy.
- Measure chia cho nhau ra trống → thiếu quan hệ trong Model view (xem 0.2).
- % hiển thị 0.23 thay vì 23% → chọn measure → Measure tools → nút %.
- Trục năm hiện "2,021" → X-axis Type: Categorical.
- Phễu sai thứ tự → bước 0.5 (Sort by column).
