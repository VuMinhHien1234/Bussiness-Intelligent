# add_2025_data.py — sinh dữ liệu giả lập năm 2025 và ghép vào masan_case.xlsx
# Cách chạy:  python3 add_2025_data.py
# Logic: lấy mẫu ngẫu nhiên các dòng 2024 (giữ nguyên tháng để khớp chiến dịch),
# đổi sang năm 2025, tăng doanh thu/chi phí ~8% có nhiễu, tính lại các cột dẫn xuất
# theo đúng công thức của dữ liệu gốc:
#   Cost = RawMaterial + Labor + Logistics + Marketing
#   Profit = Revenue - Cost ; ProfitMargin = Profit/Revenue
#   UnitCost = Cost/Qty ; RevenuePerUnit = Revenue/Qty ; CostPerMachineUnit = Cost/Qty
#   ROI_Marketing = Profit/Budget

import calendar

import numpy as np
import pandas as pd

FILE = "masan_case.xlsx"
N_ROWS = 750
GROWTH = 1.08          # 2025 ~ +8% so với 2024
SEED = 2025

np.random.seed(SEED)

df = pd.read_excel(FILE)
backup = "masan_case_backup_2023_2024.xlsx"
df.to_excel(backup, sheet_name="Sheet1", index=False)
print(f"Backup: {backup} ({len(df)} dòng)")

# Nguồn lấy mẫu: dòng 2024 sạch (đủ ngày, số liệu hợp lệ)
num = df.apply(pd.to_numeric, errors="coerce")
src = df[(num.Year == 2024)
         & pd.to_datetime(df.Date, errors="coerce").notna()
         & num.Revenue.notna() & num.Quantity.notna() & num.Budget.notna()].copy()
print(f"Nguồn mẫu 2024: {len(src)} dòng")

sample = src.sample(N_ROWS, replace=True, random_state=SEED).reset_index(drop=True)
out = sample.copy()

next_id = int(num.OrderID.max()) + 1
out["OrderID"] = range(next_id, next_id + N_ROWS)
out["Year"] = 2025

# Ngày mới: giữ tháng (khớp PromotionCampaign), ngày ngẫu nhiên trong tháng
months = pd.to_numeric(out.Month).astype(int)
days = [np.random.randint(1, calendar.monthrange(2025, m)[1] + 1) for m in months]
out["Date"] = [f"2025-{m:02d}-{d:02d}" for m, d in zip(months, days)]  # chuỗi ISO để ETL parse được

# Hệ số tăng trưởng từng dòng
g = np.random.normal(GROWTH, 0.06, N_ROWS).clip(0.9, 1.3)

money2 = lambda s: (pd.to_numeric(s, errors="coerce") * g).round(2)
for c in ["RawMaterialCost", "LaborCost", "LogisticsCost", "MarketingCost",
          "Revenue", "Budget", "Target"]:
    out[c] = money2(sample[c])

qty = pd.to_numeric(sample.Quantity, errors="coerce")
out["Quantity"] = qty
out["Cost"] = (out.RawMaterialCost + out.LaborCost
               + out.LogisticsCost + out.MarketingCost).round(2)
out["Profit"] = (out.Revenue - out.Cost).round(2)
out["ProfitMargin"] = (out.Profit / out.Revenue).round(6)
out["UnitCost"] = (out.Cost / qty).round(6)
out["RevenuePerUnit"] = (out.Revenue / qty).round(6)
out["CostPerMachineUnit"] = (out.Cost / qty).round(6)
out["ROI_Marketing"] = (out.Profit / out.Budget).round(6)

# Các chỉ số vận hành: giữ giá trị mẫu + nhiễu nhẹ
noise = lambda s, sd: (pd.to_numeric(s, errors="coerce")
                       * np.random.normal(1, sd, N_ROWS)).round(2)
out["InventoryLevel"] = noise(sample.InventoryLevel, 0.10)
out["Calls"] = noise(sample.Calls, 0.10).round(0)
out["WaitingTime"] = noise(sample.WaitingTime, 0.10)
out["ConversionProxy"] = (pd.to_numeric(sample.ConversionProxy, errors="coerce")
                          * np.random.normal(1, 0.05, N_ROWS)).round(6)
out["MarketSize"] = noise(sample.MarketSize, 0.05)
out["MarketShare"] = (pd.to_numeric(sample.MarketShare, errors="coerce")
                      * np.random.normal(1, 0.05, N_ROWS)).round(6)
out["RegionProfitShare"] = pd.to_numeric(sample.RegionProfitShare, errors="coerce")

final = pd.concat([df, out[df.columns]], ignore_index=True)
final.to_excel(FILE, sheet_name="Sheet1", index=False)
print(f"Đã ghi {FILE}: {len(df)} -> {len(final)} dòng")
print(f"Doanh thu 2025 mới: {out.Revenue.sum():,.0f} (2024: {num[num.Year==2024].Revenue.sum():,.0f})")
