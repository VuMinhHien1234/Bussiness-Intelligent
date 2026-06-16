
import os
from dotenv import load_dotenv

# Load .env from the project root (one level above this file's directory).
_dotenv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
load_dotenv(_dotenv_path)

def _resolve(env_key, default):
    """Return an absolute path, resolving relative paths against this file's directory."""
    path = os.getenv(env_key, default)
    if not os.path.isabs(path):
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), path)
    return path

# ── File paths ────────────────────────────────────────────────────────────────
EXCEL_PATH       = _resolve("EXCEL_PATH",       "vnretail_data.xlsx")
FB_ADS_CSV_PATH  = _resolve("FB_ADS_CSV_PATH",  "fb_ads_spend.csv")
WEATHER_CSV_PATH = _resolve("WEATHER_CSV_PATH", "weather_daily.csv")

# ── Database connection ───────────────────────────────────────────────────────
DB_CONFIG = {
    "user":     os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "host":     os.getenv("DB_HOST"),
    "port":     os.getenv("DB_PORT"),
    "dbname":   os.getenv("DB_NAME"),
}

# ── Schema names ──────────────────────────────────────────────────────────────
STG = os.getenv("DB_SCHEMA_STAGING", "staging")
DW  = os.getenv("DB_SCHEMA_DWH",     "dw")

# ── Staging table names ───────────────────────────────────────────────────────
STG_SALES   = os.getenv("RAW_TABLE",         "vnretail_data_xlsx")
STG_ADS     = os.getenv("FB_ADS_RAW_TABLE",  "fb_ads_csv")
STG_WEATHER = os.getenv("WEATHER_RAW_TABLE", "weather_csv")

# ── DW dimension table names ──────────────────────────────────────────────────
DIM_DATE     = os.getenv("MARKETING_DIM_DATE_TABLE",             "dim_date")
DIM_STAGE    = os.getenv("MARKETING_DIM_STAGE_TABLE",            "dim_stage")
DIM_CHANNEL  = os.getenv("MARKETING_DIM_CHANNEL_TABLE",          "dim_channel")
DIM_SEGMENT  = os.getenv("MARKETING_DIM_CUSTOMER_SEGMENT_TABLE", "dim_customer_segment")
DIM_CAMPAIGN = os.getenv("MARKETING_DIM_CAMPAIGN_TABLE",         "dim_campaign")
DIM_DEPT     = os.getenv("MARKETING_DIM_DEPARTMENT_TABLE",       "dim_department")
DIM_MACHINE  = os.getenv("MARKETING_DIM_MACHINE_TABLE",          "dim_machine")
DIM_INFO     = os.getenv("MARKETING_DIM_INFORMATION_TABLE",      "dim_information")
DIM_REGION   = os.getenv("MARKETING_DIM_REGION_TABLE",           "dim_region")
DIM_BRANCH   = os.getenv("MARKETING_DIM_BRANCH_TABLE",           "dim_branch")
DIM_PRODUCT  = os.getenv("MARKETING_DIM_PRODUCT_TABLE",          "dim_product")

# ── DW fact table names ───────────────────────────────────────────────────────
FACT_SALES   = os.getenv("FACT_MARKETING_TABLE", "fact_marketing_sales")
FACT_ADS     = os.getenv("FACT_AD_SPEND_TABLE",  "fact_ad_spend")
FACT_WEATHER = os.getenv("FACT_WEATHER_TABLE",   "fact_weather_daily")

# ── Business lookup maps ──────────────────────────────────────────────────────

# Maps Facebook Ads campaign slugs (from CSV) to canonical display names.
CAMPAIGN_SLUG_MAP = {
    "tet_promotion":       "Tet Promotion",
    "spring_campaign":     "Spring Campaign",
    "summer_promotion":    "Summer Promotion",
    "back_to_school":      "Back-to-School",
    "mid_autumn_campaign": "Mid-Autumn Campaign",
    "year_end_promotion":  "Year-End Promotion",
}

# Maps canonical campaign names to their campaign type category.
CAMPAIGN_TYPE_MAP = {
    "Tet Promotion":       "Seasonal",
    "Spring Campaign":     "Seasonal",
    "Summer Promotion":    "Seasonal",
    "Mid-Autumn Campaign": "Seasonal",
    "Year-End Promotion":  "Year end",
    "Back-to-School":      "Back to school",
}

# Fixed funnel stage vocabulary with ordering and grouping.
STAGE_ORDER = {
    "Impression":    (1, "Awareness"),
    "Visit website": (2, "Consideration"),
    "Click":         (3, "Consideration"),
    "Add to cart":   (4, "Intent"),
    "Purchase":      (5, "Conversion"),
}

# Maps sales channel names to their channel type category.
CHANNEL_TYPE = {
    "Facebook":         "Social",
    "Ecommerce":        "Digital commerce",
    "TV":               "Broadcast",
    "Retail promotion": "Trade promotion",
    "Traditional trade":"Traditional trade",
    "Other":            "Other",
}

# Maps canonical column names to accepted raw-source variants (for fuzzy matching).
COLUMN_ALIASES = {
    "order_id":             ["orderid", "order_id"],
    "date":                 ["date", "ngay"],
    "year":                 ["year", "nam"],
    "month":                ["month", "thang"],
    "region":               ["region", "vung"],
    "branch":               ["branch", "chinhanh"],
    "department":           ["department", "phongban", "bo phan"],
    "product":              ["product", "sanpham"],
    "category":             ["category", "danhmuc"],
    "stage":                ["stage", "funnelstage", "giai doan"],
    "channel":              ["channel", "kenh"],
    "information":          ["information", "thongtin"],
    "machine":              ["machine", "may"],
    "quantity":             ["quantity", "soluong"],
    "revenue":              ["revenue", "doanhthu"],
    "cost":                 ["cost", "chiphi"],
    "profit":               ["profit", "loinhuan"],
    "profit_margin":        ["profitmargin", "profit_margin", "bienloinhuan"],
    "inventory_level":      ["inventorylevel", "inventory_level", "tonkho"],
    "calls":                ["calls", "cuocgoi"],
    "waiting_time":         ["waitingtime", "waiting_time", "thoigiancho"],
    "budget":               ["budget", "ngansach"],
    "target":               ["target", "muctieu"],
    "raw_material_cost":    ["rawmaterialcost", "raw_material_cost"],
    "labor_cost":           ["laborcost", "labor_cost"],
    "logistics_cost":       ["logisticscost", "logistics_cost", "chiphilogistics"],
    "marketing_cost":       ["marketingcost", "marketing_cost", "chiphimarketing"],
    "unit_cost":            ["unitcost", "unit_cost"],
    "revenue_per_unit":     ["revenueperunit", "revenue_per_unit"],
    "roi_marketing":        ["roimarketing", "roi_marketing", "roi marketing"],
    "conversion_proxy":     ["conversionproxy", "conversion_proxy"],
    "cost_per_machine_unit":["costpermachineunit", "cost_per_machine_unit"],
    "region_profit_share":  ["regionprofitshare", "region_profit_share"],
    "market_size":          ["marketsize", "market_size", "quymothitruong"],
    "market_share":         ["marketshare", "market_share"],
    "customer_segment":     ["customersegment", "customer_segment", "phan khuc khach hang"],
    "campaign":             ["promotioncampaign", "promotion_campaign", "campaignname",
                             "campaign_name", "chien dich"],
}
