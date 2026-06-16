
import pandas as pd
from config import (
    DW, COLUMN_ALIASES, STAGE_ORDER, CHANNEL_TYPE,
    DIM_DATE, DIM_STAGE, DIM_CHANNEL, DIM_SEGMENT, DIM_CAMPAIGN,
    DIM_DEPT, DIM_MACHINE, DIM_INFO, DIM_REGION, DIM_BRANCH, DIM_PRODUCT,
    FACT_SALES,
)
from utils import tbl, to_none, to_records, upsert, normalize_col, classify_campaign, parse_dates, build_dim_date_df


# ── Column standardization ────────────────────────────────────────────────────

REQUIRED_COLS = ["order_id", "date", "channel", "stage", "revenue"]

OPTIONAL_COLS = [
    "year", "month", "region", "branch", "department", "product", "category",
    "information", "machine", "quantity", "cost", "profit", "profit_margin",
    "inventory_level", "calls", "waiting_time", "budget", "target",
    "raw_material_cost", "labor_cost", "logistics_cost", "marketing_cost",
    "unit_cost", "revenue_per_unit", "roi_marketing", "conversion_proxy",
    "cost_per_machine_unit", "region_profit_share", "market_size",
    "market_share", "customer_segment", "campaign",
]

ALL_COLS = REQUIRED_COLS + [c for c in OPTIONAL_COLS if c not in REQUIRED_COLS]


def standardize_columns(df):
    normalized_src = {normalize_col(c): c for c in df.columns}

    rename = {}
    for canonical, aliases in COLUMN_ALIASES.items():
        for alias in aliases:
            src = normalized_src.get(normalize_col(alias))
            if src:
                rename[src] = canonical
                break

    df = df.rename(columns=rename)

    missing = [c for c in REQUIRED_COLS if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns after mapping: {missing}")

    for col in OPTIONAL_COLS:
        if col not in df.columns:
            df[col] = None

    return df[ALL_COLS]


# ── Cleaning ──────────────────────────────────────────────────────────────────

def clean_sales_data(df):
    df = standardize_columns(df).copy()

    # Step 2: Parse dates.
    df["date"] = parse_dates(df["date"])

    # Step 3: Normalize text dimensions.
    text_cols = [
        "region", "branch", "department", "product", "category",
        "stage", "channel", "information", "machine", "customer_segment", "campaign",
    ]
    for col in text_cols:
        df[col] = (df[col].astype("string").str.strip()
                   .replace({"": pd.NA, "nan": pd.NA, "None": pd.NA}))

    # Step 4: Cast numeric columns.
    num_cols = [
        "order_id", "year", "month", "quantity", "revenue", "cost", "profit",
        "profit_margin", "inventory_level", "calls", "waiting_time", "budget",
        "target", "raw_material_cost", "labor_cost", "logistics_cost",
        "marketing_cost", "unit_cost", "revenue_per_unit", "roi_marketing",
        "conversion_proxy", "cost_per_machine_unit", "region_profit_share",
        "market_size", "market_share",
    ]
    for col in num_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # Step 5: Drop rows with missing critical fields.
    drop_reasons = {
        "order_id missing/invalid": df["order_id"].isna(),
        "date missing/invalid":     df["date"].isna(),
        "channel missing":          df["channel"].isna(),
        "stage missing":            df["stage"].isna(),
        "revenue missing":          df["revenue"].isna(),
    }
    bad = pd.Series(False, index=df.index)
    for reason, mask in drop_reasons.items():
        count = int((mask & ~bad).sum())
        if count:
            print(f"  Dropping {count} rows: {reason}")
        bad |= mask
    df = df[~bad]
    df["order_id"] = df["order_id"].astype("int64")

    # Derive year/month from the cleaned date to avoid source-column mismatch.
    df["year"]  = pd.to_datetime(df["date"]).dt.year
    df["month"] = pd.to_datetime(df["date"]).dt.month

    # Step 6: Deduplicate on order_id.
    before = len(df)
    df = df.drop_duplicates(subset=["order_id"], keep="last")
    if (dropped := before - len(df)):
        print(f"  Deduplication: removed {dropped} duplicate order_id rows (kept last)")

    return df.astype(object).where(pd.notnull(df), None)


# ── Dimension loading ─────────────────────────────────────────────────────────

def load_dimensions(conn, df):
    """Upsert all 11 conformed dimension tables from the cleaned sales DataFrame."""
    with conn.cursor() as cur:

        # dim_date
        upsert(cur, f"""
            INSERT INTO {tbl(DW, DIM_DATE)}
                (full_date, year, month, month_name, quarter, year_month)
            VALUES %s
            ON CONFLICT (full_date) DO UPDATE SET
                year=EXCLUDED.year, month=EXCLUDED.month,
                month_name=EXCLUDED.month_name, quarter=EXCLUDED.quarter,
                year_month=EXCLUDED.year_month
            """,
            to_records(build_dim_date_df(df["date"])),
        )

        # dim_stage: fixed vocabulary + any unknown stages from source
        known = [(name, order, group) for name, (order, group) in STAGE_ORDER.items()]
        extra = [(s, 99, "Other") for s in df["stage"].dropna().drop_duplicates()
                 if s not in STAGE_ORDER]
        upsert(cur, f"""
            INSERT INTO {tbl(DW, DIM_STAGE)} (stage_name, stage_order, stage_group)
            VALUES %s
            ON CONFLICT (stage_name) DO UPDATE SET
                stage_order=EXCLUDED.stage_order, stage_group=EXCLUDED.stage_group
            """,
            known + extra,
        )

        # dim_channel
        upsert(cur, f"""
            INSERT INTO {tbl(DW, DIM_CHANNEL)} (channel_name, channel_type)
            VALUES %s
            ON CONFLICT (channel_name) DO UPDATE SET channel_type=EXCLUDED.channel_type
            """,
            [(ch, CHANNEL_TYPE.get(ch, "Other"))
             for ch in df["channel"].dropna().drop_duplicates()],
        )

        # dim_customer_segment
        upsert(cur, f"""
            INSERT INTO {tbl(DW, DIM_SEGMENT)} (segment_name) VALUES %s
            ON CONFLICT (segment_name) DO NOTHING
            """,
            [(to_none(x),) for x in df["customer_segment"].dropna().drop_duplicates()],
        )

        # dim_campaign
        upsert(cur, f"""
            INSERT INTO {tbl(DW, DIM_CAMPAIGN)} (campaign_name, campaign_type)
            VALUES %s
            ON CONFLICT (campaign_name) DO UPDATE SET campaign_type=EXCLUDED.campaign_type
            """,
            [(c, classify_campaign(c)) for c in df["campaign"].dropna().drop_duplicates()],
        )

        # dim_department, dim_machine, dim_information (name-only dimensions)
        for dim_table, col, col_name in [
            (DIM_DEPT,    "department",  "department_name"),
            (DIM_MACHINE, "machine",     "machine_name"),
            (DIM_INFO,    "information", "information_name"),
        ]:
            upsert(cur, f"""
                INSERT INTO {tbl(DW, dim_table)} ({col_name}) VALUES %s
                ON CONFLICT ({col_name}) DO NOTHING
                """,
                [(to_none(x),) for x in df[col].dropna().drop_duplicates()],
            )

        # dim_region
        upsert(cur, f"""
            INSERT INTO {tbl(DW, DIM_REGION)} (region_name) VALUES %s
            ON CONFLICT (region_name) DO NOTHING
            """,
            [(to_none(x),) for x in df["region"].dropna().drop_duplicates()],
        )

        # dim_branch (branch + region)
        branch_df = (df[["branch", "region"]]
                     .dropna(subset=["branch"])
                     .drop_duplicates(subset=["branch"]))
        upsert(cur, f"""
            INSERT INTO {tbl(DW, DIM_BRANCH)} (branch_name, region_name)
            VALUES %s
            ON CONFLICT (branch_name) DO UPDATE SET region_name=EXCLUDED.region_name
            """,
            to_records(branch_df),
        )

        # dim_product (product + category)
        product_df = (df[["product", "category"]]
                      .dropna(subset=["product"])
                      .drop_duplicates(subset=["product"]))
        upsert(cur, f"""
            INSERT INTO {tbl(DW, DIM_PRODUCT)} (product_name, category_name)
            VALUES %s
            ON CONFLICT (product_name) DO UPDATE SET category_name=EXCLUDED.category_name
            """,
            to_records(product_df),
        )

    conn.commit()


# ── Fact loading ──────────────────────────────────────────────────────────────

def load_fact_sales(conn, df):
    fact_cols = [
        "order_id", "date", "stage", "channel", "information", "machine",
        "department", "customer_segment", "campaign", "branch", "product",
        "quantity", "revenue", "cost", "profit", "profit_margin",
        "inventory_level", "calls", "waiting_time", "conversion_proxy",
        "budget", "target", "marketing_cost", "roi_marketing",
        "raw_material_cost", "labor_cost", "logistics_cost", "unit_cost",
        "revenue_per_unit", "cost_per_machine_unit", "market_size",
        "market_share", "region_profit_share",
    ]
    with conn.cursor() as cur:
        upsert(cur, f"""
            INSERT INTO {tbl(DW, FACT_SALES)} (
                order_id, full_date, stage_name, channel_name, information_name,
                machine_name, department_name, segment_name, campaign_name,
                branch_name, product_name, quantity,
                revenue, cost, profit, profit_margin, inventory_level, calls,
                waiting_time, conversion_proxy, budget, target, marketing_cost,
                roi_marketing, raw_material_cost, labor_cost, logistics_cost,
                unit_cost, revenue_per_unit, cost_per_machine_unit,
                market_size, market_share, region_profit_share
            )
            VALUES %s
            ON CONFLICT (order_id) DO UPDATE SET
                full_date=EXCLUDED.full_date,
                stage_name=EXCLUDED.stage_name,
                channel_name=EXCLUDED.channel_name,
                information_name=EXCLUDED.information_name,
                machine_name=EXCLUDED.machine_name,
                department_name=EXCLUDED.department_name,
                segment_name=EXCLUDED.segment_name,
                campaign_name=EXCLUDED.campaign_name,
                branch_name=EXCLUDED.branch_name,
                product_name=EXCLUDED.product_name,
                quantity=EXCLUDED.quantity,
                revenue=EXCLUDED.revenue,
                cost=EXCLUDED.cost,
                profit=EXCLUDED.profit,
                profit_margin=EXCLUDED.profit_margin,
                inventory_level=EXCLUDED.inventory_level,
                calls=EXCLUDED.calls,
                waiting_time=EXCLUDED.waiting_time,
                conversion_proxy=EXCLUDED.conversion_proxy,
                budget=EXCLUDED.budget,
                target=EXCLUDED.target,
                marketing_cost=EXCLUDED.marketing_cost,
                roi_marketing=EXCLUDED.roi_marketing,
                raw_material_cost=EXCLUDED.raw_material_cost,
                labor_cost=EXCLUDED.labor_cost,
                logistics_cost=EXCLUDED.logistics_cost,
                unit_cost=EXCLUDED.unit_cost,
                revenue_per_unit=EXCLUDED.revenue_per_unit,
                cost_per_machine_unit=EXCLUDED.cost_per_machine_unit,
                market_size=EXCLUDED.market_size,
                market_share=EXCLUDED.market_share,
                region_profit_share=EXCLUDED.region_profit_share
            """,
            to_records(df[fact_cols]),
        )
    conn.commit()
