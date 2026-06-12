# adjust_sales_by_weather.py — "cài" tính mùa vụ vào masan_case.xlsx theo thời tiết THẬT
# Chạy SAU khi đã có weather_daily.csv (python3 fetch_weather.py), và CHỈ CHẠY 1 LẦN:
#   python3 adjust_sales_by_weather.py
#
# Logic: với mỗi đơn hàng (có ngày + vùng + ngành hàng hợp lệ), tra nhiệt độ trung bình
# của vùng đó đúng ngày đó, rồi co giãn sản lượng/doanh thu theo độ nhạy của ngành hàng:
#   Kem       +6.0%/°C so với mốc 26°C  (nhạy mạnh)
#   Sữa chua  +2.5%/°C                  (nhạy vừa)
#   Sữa tươi  +1.2%/°C                  (nhạy nhẹ)
#   Sữa bột    0%                       (không nhạy - sữa công thức cho bé)
# Sau đó tính lại toàn bộ cột dẫn xuất theo đúng công thức gốc của dữ liệu.

import os
import re
import sys

import numpy as np
import pandas as pd

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
EXCEL = sys.argv[1] if len(sys.argv) > 1 else os.path.join(BASE_DIR, "masan_case.xlsx")
WEATHER = sys.argv[2] if len(sys.argv) > 2 else os.path.join(BASE_DIR, "weather_daily.csv")
MARKER = EXCEL + ".weather_adjusted"

BASE_TEMP = 26.0
SENSITIVITY = {  # %/°C theo ngành hàng
    "Kem": 0.060,
    "Sữa chua": 0.025,
    "Sữa tươi": 0.012,
    "Sữa bột": 0.0,
}
np.random.seed(26)


def parse_date(v):
    s = str(v).strip()
    if re.match(r"^\d{4}-\d{1,2}-\d{1,2}", s):
        return pd.to_datetime(s[:10], errors="coerce", format="%Y-%m-%d")
    return pd.to_datetime(s, errors="coerce", dayfirst=True)


def main():
    if os.path.exists(MARKER):
        print("Dữ liệu đã được điều chỉnh trước đó — không chạy lại để tránh méo thêm.")
        print(f"(Muốn ép chạy lại: xóa file {os.path.basename(MARKER)} và khôi phục backup trước.)")
        return

    if not os.path.exists(WEATHER):
        print(f"Chưa có {os.path.basename(WEATHER)} — chạy 'python3 fetch_weather.py' trước.")
        sys.exit(1)

    weather = pd.read_csv(WEATHER)
    weather["date"] = pd.to_datetime(weather["date"])
    temp_lookup = {
        (d.date(), r): t
        for d, r, t in zip(weather["date"], weather["region"], weather["temp_mean"])
        if pd.notna(t)
    }
    print(f"Thời tiết: {len(weather)} dòng, {weather['region'].nunique()} vùng")

    df = pd.read_excel(EXCEL)
    backup = EXCEL.replace(".xlsx", "_backup_truoc_thoitiet.xlsx")
    pd.read_excel(EXCEL).to_excel(backup, sheet_name="Sheet1", index=False)
    print(f"Backup: {os.path.basename(backup)}")

    # Bước 1: khử mùa vụ ngẫu nhiên cũ (spike do khuyến mãi trong dữ liệu giả lập)
    # để mùa vụ mới đến thuần từ nhiệt độ: hệ số = TB cả năm / TB tháng đó (theo ngành hàng).
    rev_all = pd.to_numeric(df["Revenue"], errors="coerce")
    mon_all = pd.to_numeric(df["Month"], errors="coerce")
    cat_all = df["Category"].astype(str).str.strip()
    deseason = {}
    for cat in SENSITIVITY:
        mask = cat_all == cat
        overall = rev_all[mask].mean()
        for m in range(1, 13):
            month_mean = rev_all[mask & (mon_all == m)].mean()
            deseason[(cat, m)] = (overall / month_mean) if month_mean and pd.notna(month_mean) else 1.0

    adjusted = skipped = 0
    for i in df.index:
        cat = str(df.at[i, "Category"]).strip()
        region = str(df.at[i, "Region"]).strip()
        d = parse_date(df.at[i, "Date"])
        qty = pd.to_numeric(df.at[i, "Quantity"], errors="coerce")
        rev = pd.to_numeric(df.at[i, "Revenue"], errors="coerce")

        if cat not in SENSITIVITY or pd.isna(d) or pd.isna(qty) or pd.isna(rev) or qty <= 0:
            skipped += 1
            continue
        temp = temp_lookup.get((d.date(), region))
        if temp is None:
            skipped += 1
            continue

        f = deseason.get((cat, int(d.month)), 1.0) \
            * (1 + SENSITIVITY[cat] * (temp - BASE_TEMP) + np.random.normal(0, 0.02))
        f = float(np.clip(f, 0.30, 2.60))
        new_qty = max(1, int(round(qty * f)))
        realized = new_qty / qty  # hệ số thực sau khi làm tròn sản lượng

        cols_scale = ["Revenue", "RawMaterialCost", "LaborCost", "LogisticsCost", "MarketingCost"]
        vals = {c: pd.to_numeric(df.at[i, c], errors="coerce") for c in cols_scale}
        if any(pd.isna(v) for v in vals.values()):
            skipped += 1
            continue

        new = {c: round(v * realized, 2) for c, v in vals.items()}
        cost = round(sum(new[c] for c in cols_scale[1:]), 2)
        profit = round(new["Revenue"] - cost, 2)
        budget = pd.to_numeric(df.at[i, "Budget"], errors="coerce")

        df.at[i, "Quantity"] = new_qty
        for c in cols_scale:
            df.at[i, c] = new[c]
        df.at[i, "Cost"] = cost
        df.at[i, "Profit"] = profit
        df.at[i, "ProfitMargin"] = round(profit / new["Revenue"], 6) if new["Revenue"] else None
        df.at[i, "UnitCost"] = round(cost / new_qty, 6)
        df.at[i, "RevenuePerUnit"] = round(new["Revenue"] / new_qty, 6)
        df.at[i, "CostPerMachineUnit"] = round(cost / new_qty, 6)
        if pd.notna(budget) and budget:
            df.at[i, "ROI_Marketing"] = round(profit / budget, 6)
        adjusted += 1

    df.to_excel(EXCEL, sheet_name="Sheet1", index=False)
    open(MARKER, "w").write("done")
    print(f"Đã điều chỉnh {adjusted} dòng theo nhiệt độ, giữ nguyên {skipped} dòng "
          f"(thiếu ngày/vùng/ngành hàng hợp lệ).")
    print(f"Đã ghi {os.path.basename(EXCEL)}. Giờ chạy ./run_etl.sh để nạp vào database.")


if __name__ == "__main__":
    main()
