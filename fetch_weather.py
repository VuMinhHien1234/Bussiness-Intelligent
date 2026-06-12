# fetch_weather.py — Nguồn 3: tải thời tiết thật từ Open-Meteo API (miễn phí, không cần key)
# Cách chạy:  python3 fetch_weather.py
# Kết quả:    weather_daily.csv (ngày x vùng: nhiệt độ TB, nhiệt độ max, lượng mưa)

import csv
import json
import sys
import urllib.request

START = "2021-01-01"
END = "2025-12-31"

# Mỗi miền lấy theo thành phố đại diện (khớp cột Region trong masan_case.xlsx).
REGIONS = {
    "Miền Bắc": (21.0285, 105.8542),   # Hà Nội
    "Miền Trung": (16.0544, 108.2022), # Đà Nẵng
    "Miền Nam": (10.7626, 106.6602),   # TP.HCM
}

URL = (
    "https://archive-api.open-meteo.com/v1/archive"
    "?latitude={lat}&longitude={lon}"
    f"&start_date={START}&end_date={END}"
    "&daily=temperature_2m_mean,temperature_2m_max,precipitation_sum"
    "&timezone=Asia%2FBangkok"
)


def fetch(region, lat, lon):
    url = URL.format(lat=lat, lon=lon)
    print(f"Tải {region} ({lat}, {lon})...")
    with urllib.request.urlopen(url, timeout=60) as resp:
        data = json.load(resp)
    daily = data["daily"]
    return [
        {
            "date": d,
            "region": region,
            "temp_mean": tm,
            "temp_max": tx,
            "rain_mm": rain,
        }
        for d, tm, tx, rain in zip(
            daily["time"],
            daily["temperature_2m_mean"],
            daily["temperature_2m_max"],
            daily["precipitation_sum"],
        )
    ]


def main():
    rows = []
    for region, (lat, lon) in REGIONS.items():
        rows.extend(fetch(region, lat, lon))

    out = "weather_daily.csv"
    with open(out, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f, fieldnames=["date", "region", "temp_mean", "temp_max", "rain_mm"]
        )
        writer.writeheader()
        writer.writerows(rows)
    print(f"Đã ghi {out}: {len(rows)} dòng ({len(REGIONS)} vùng x số ngày)")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"Lỗi khi tải thời tiết: {exc}")
        sys.exit(1)
