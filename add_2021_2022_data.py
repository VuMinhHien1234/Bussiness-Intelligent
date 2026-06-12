# add_2021_2022_data.py — sinh dữ liệu lịch sử 2021–2022 và ghép vào masan_case.xlsx
# Cách chạy:  python3 add_2021_2022_data.py   (chỉ chạy 1 lần)
# Logic: lấy mẫu các dòng 2023 (đã mang tính mùa vụ theo thời tiết), giữ nguyên tháng
# để khớp chiến dịch, đổi năm về 2021/2022 với doanh thu giảm dần về quá khứ
# (2022 ≈ 93%, 2021 ≈ 86% mức 2023), tính lại toàn bộ cột dẫn xuất theo công thức gốc.

import calendar
import os

import numpy as np
import pandas as pd

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FILE = os.path.join(BASE_DIR, "masan_case.xlsx")
MARKER = FILE + ".added_2021_2022"
N_PER_YEAR = 750
YEAR_SCALE = {2021: 0.86, 2022: 0.93}   # so với mức 2023
ID_START = {2021: 17000, 2022: 18500}   # thấp hơn dải 20000+ hiện có
SEED = 2122

np.random.seed(SEED)

if os.path.exists(MARKER):
    print("Đã thêm 2021–2022 trước đó — không chạy lại để tránh nhân đôi dữ liệu.")
    raise SystemExit(0)

df = pd.read_excel(FILE)
backup = FILE.replace(".xlsx", "_backup_truoc_2021.xlsx")
df.to_excel(backup, sheet_name="Sheet1", index=False)
print(f"Backup: {os.path.basename(backup)} ({len(df)} dòng)")

num = df.apply(pd.to_numeric, errors="coerce")
src = df[(num.Year == 2023)
         & pd.to_datetime(df.Date, errors="coerce").notna()
         & num.Revenue.notna() & num.Quantity.notna() & num.Budget.notna()].copy()
print(f"Nguồn mẫu 2023: {len(src)} dòng")

parts = [df]
for year in (2021, 2022):
    sample = src.sample(N_PER_YEAR, replace=True, random_state=SEED + year).reset_index(drop=True)
    out = sample.copy()
    out["OrderID"] = range(ID_START[year], ID_START[year] + N_PER_YEAR)
    out["Year"] = year

    months = pd.to_numeric(out.Month).astype(int)
    days = [np.random.randint(1, calendar.monthrange(year, m)[1] + 1) for m in months]
    out["Date"] = [f"{year}-{m:02d}-{d:02d}" for m, d in zip(months, days)]  # chuỗi ISO

    g = np.random.normal(YEAR_SCALE[year], 0.06, N_PER_YEAR).clip(0.6, 1.2)
    money = lambda s: (pd.to_numeric(s, errors="coerce") * g).round(2)
    for c in ["RawMaterialCost", "LaborCost", "LogisticsCost", "MarketingCost",
              "Revenue", "Budget", "Target"]:
        out[c] = money(sample[c])

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

    noise = lambda s, sd: (pd.to_numeric(s, errors="coerce")
                           * np.random.normal(1, sd, N_PER_YEAR)).round(2)
    out["InventoryLevel"] = noise(sample.InventoryLevel, 0.10)
    out["Calls"] = noise(sample.Calls, 0.10).round(0)
    out["WaitingTime"] = noise(sample.WaitingTime, 0.10)
    out["ConversionProxy"] = (pd.to_numeric(sample.ConversionProxy, errors="coerce")
                              * np.random.normal(1, 0.05, N_PER_YEAR)).round(6)
    out["MarketSize"] = noise(sample.MarketSize, 0.05)
    out["MarketShare"] = (pd.to_numeric(sample.MarketShare, errors="coerce")
                          * np.random.normal(1, 0.05, N_PER_YEAR)).round(6)
    out["RegionProfitShare"] = pd.to_numeric(sample.RegionProfitShare, errors="coerce")

    parts.append(out[df.columns])
    print(f"Năm {year}: +{N_PER_YEAR} dòng, doanh thu {out.Revenue.sum():,.0f}")

final = pd.concat(parts, ignore_index=True).sort_values("OrderID").reset_index(drop=True)
final.to_excel(FILE, sheet_name="Sheet1", index=False)
open(MARKER, "w").write("done")
print(f"Đã ghi {os.path.basename(FILE)}: {len(df)} -> {len(final)} dòng")
