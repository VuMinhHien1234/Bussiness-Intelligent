
import pandas as pd
from config import (
    DW, CAMPAIGN_SLUG_MAP,
    DIM_DATE, DIM_CAMPAIGN, DIM_CHANNEL, FACT_ADS,
)
from utils import tbl, to_records, upsert, classify_campaign, parse_dates, build_dim_date_df


def clean_ads_data(df):
    df = df.copy()
    before = len(df)

    df["date"]     = parse_dates(df["date"])
    df["campaign"] = (df["campaign"].astype("string").str.strip()
                      .str.lower().map(CAMPAIGN_SLUG_MAP))

    for col in ["spend", "impressions", "clicks", "conversions"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df.dropna(subset=["date", "campaign", "spend"])
    df = df.groupby(["date", "campaign"], as_index=False).agg(
        spend=("spend", "sum"),
        impressions=("impressions", "sum"),
        clicks=("clicks", "sum"),
        conversions=("conversions", "sum"),
    )

    print(f"  Ads: {before} raw rows → {len(df)} after cleaning and deduplication")
    return df


def load_fact_ad_spend(conn, ads_df):
    with conn.cursor() as cur:

        # Ensure ad-only dates exist in dim_date.
        upsert(cur, f"""
            INSERT INTO {tbl(DW, DIM_DATE)}
                (full_date, year, month, month_name, quarter, year_month)
            VALUES %s
            ON CONFLICT (full_date) DO NOTHING
            """,
            to_records(build_dim_date_df(ads_df["date"])),
        )

        # Ensure campaigns exist in dim_campaign (conformed with sales source).
        upsert(cur, f"""
            INSERT INTO {tbl(DW, DIM_CAMPAIGN)} (campaign_name, campaign_type)
            VALUES %s
            ON CONFLICT (campaign_name) DO NOTHING
            """,
            [(c, classify_campaign(c)) for c in ads_df["campaign"].drop_duplicates()],
        )

        # Ensure the Facebook channel exists in dim_channel.
        cur.execute(f"""
            INSERT INTO {tbl(DW, DIM_CHANNEL)} (channel_name, channel_type)
            VALUES ('Facebook', 'Social')
            ON CONFLICT (channel_name) DO NOTHING
        """)

        # Upsert fact rows.
        fact_df = ads_df.assign(channel="Facebook")[
            ["date", "campaign", "channel", "spend", "impressions", "clicks", "conversions"]
        ]
        upsert(cur, f"""
            INSERT INTO {tbl(DW, FACT_ADS)} (
                full_date, campaign_name, channel_name,
                spend, impressions, clicks, conversions
            )
            VALUES %s
            ON CONFLICT (full_date, campaign_name) DO UPDATE SET
                channel_name=EXCLUDED.channel_name,
                spend=EXCLUDED.spend,
                impressions=EXCLUDED.impressions,
                clicks=EXCLUDED.clicks,
                conversions=EXCLUDED.conversions
            """,
            to_records(fact_df),
        )

    conn.commit()
