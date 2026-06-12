CREATE SCHEMA IF NOT EXISTS staging;
CREATE SCHEMA IF NOT EXISTS dw;

DROP VIEW IF EXISTS dw.v_sales_weather;
DROP TABLE IF EXISTS dw.fact_weather_daily;
DROP TABLE IF EXISTS dw.fact_ad_spend;
DROP TABLE IF EXISTS dw.fact_marketing_sales;
DROP TABLE IF EXISTS dw.dim_branch;
DROP TABLE IF EXISTS dw.dim_region;
DROP TABLE IF EXISTS dw.dim_product;
DROP TABLE IF EXISTS dw.dim_information;
DROP TABLE IF EXISTS dw.dim_machine;
DROP TABLE IF EXISTS dw.dim_department;
DROP TABLE IF EXISTS dw.dim_campaign;
DROP TABLE IF EXISTS dw.dim_customer_segment;
DROP TABLE IF EXISTS dw.dim_channel;
DROP TABLE IF EXISTS dw.dim_stage;
DROP TABLE IF EXISTS dw.dim_date;
DROP TABLE IF EXISTS staging.vinamilk_case_xlsx; -- tên cũ, giữ để dọn bản cài trước
DROP TABLE IF EXISTS staging.masan_case_xlsx;
DROP TABLE IF EXISTS staging.fb_ads_csv;
DROP TABLE IF EXISTS staging.weather_csv;

-- ============================================================
-- STAGING (raw Excel load)
-- ============================================================

CREATE TABLE staging.masan_case_xlsx (
    "OrderID"            TEXT,
    "Date"               TEXT,
    "Year"               TEXT,
    "Month"              TEXT,
    "Region"             TEXT,
    "Branch"             TEXT,
    "Department"         TEXT,
    "Product"            TEXT,
    "Category"           TEXT,
    "Stage"              TEXT,
    "Channel"            TEXT,
    "Information"        TEXT,
    "Machine"            TEXT,
    "Quantity"           TEXT,
    "Revenue"            TEXT,
    "Cost"               TEXT,
    "Profit"             TEXT,
    "ProfitMargin"       TEXT,
    "InventoryLevel"     TEXT,
    "Calls"              TEXT,
    "WaitingTime"        TEXT,
    "Budget"             TEXT,
    "Target"             TEXT,
    "RawMaterialCost"    TEXT,
    "LaborCost"          TEXT,
    "LogisticsCost"      TEXT,
    "MarketingCost"      TEXT,
    "UnitCost"           TEXT,
    "RevenuePerUnit"     TEXT,
    "ROI_Marketing"      TEXT,
    "ConversionProxy"    TEXT,
    "CostPerMachineUnit" TEXT,
    "RegionProfitShare"  TEXT,
    "MarketSize"         TEXT,
    "MarketShare"        TEXT,
    "CustomerSegment"    TEXT,
    "PromotionCampaign"  TEXT
);

-- Nguồn 2: file CSV xuất từ Facebook Ads (giả lập)
CREATE TABLE staging.fb_ads_csv (
    "date"         TEXT,
    "campaign"     TEXT,
    "spend"        TEXT,
    "impressions"  TEXT,
    "clicks"       TEXT,
    "conversions"  TEXT
);

-- Nguồn 3: thời tiết theo ngày x vùng (Open-Meteo API)
CREATE TABLE staging.weather_csv (
    "date"       TEXT,
    "region"     TEXT,
    "temp_mean"  TEXT,
    "temp_max"   TEXT,
    "rain_mm"    TEXT
);

-- ============================================================
-- DIMENSIONS
-- ============================================================

CREATE TABLE dw.dim_region (
    region_name    VARCHAR(50) PRIMARY KEY
);

CREATE TABLE dw.dim_branch (
    branch_name    VARCHAR(100) PRIMARY KEY,
    region_name    VARCHAR(50) REFERENCES dw.dim_region(region_name)
);

CREATE TABLE dw.dim_product (
    product_name   VARCHAR(150) PRIMARY KEY,
    category_name  VARCHAR(100)
);

CREATE TABLE dw.dim_date (
    full_date      DATE PRIMARY KEY,
    year           INT NOT NULL,
    month          INT NOT NULL,
    month_name     VARCHAR(20),
    quarter        INT,
    year_month     VARCHAR(7)
);


CREATE TABLE dw.dim_stage (
    stage_name     VARCHAR(50) PRIMARY KEY,
    stage_order    INT NOT NULL,
    stage_group    VARCHAR(50)
);

INSERT INTO dw.dim_stage (stage_name, stage_order, stage_group)
VALUES
    ('Impression', 1, 'Awareness'),
    ('Visit website', 2, 'Consideration'),
    ('Click', 3, 'Consideration'),
    ('Add to cart', 4, 'Intent'),
    ('Purchase', 5, 'Conversion')
ON CONFLICT (stage_name) DO UPDATE SET
    stage_order = EXCLUDED.stage_order,
    stage_group = EXCLUDED.stage_group;

CREATE TABLE dw.dim_channel (
    channel_name   VARCHAR(100) PRIMARY KEY,
    channel_type   VARCHAR(50)
);

CREATE TABLE dw.dim_customer_segment (
    segment_name   VARCHAR(100) PRIMARY KEY
);

CREATE TABLE dw.dim_campaign (
    campaign_name  VARCHAR(150) PRIMARY KEY,
    campaign_type  VARCHAR(100)
);

CREATE TABLE dw.dim_department (
    department_name VARCHAR(100) PRIMARY KEY
);

CREATE TABLE dw.dim_machine (
    machine_name   VARCHAR(50) PRIMARY KEY
);

CREATE TABLE dw.dim_information (
    information_name VARCHAR(150) PRIMARY KEY
);

-- ============================================================
-- FACT TABLE
-- ============================================================

CREATE TABLE dw.fact_marketing_sales (
    order_id               BIGINT PRIMARY KEY,

    full_date              DATE REFERENCES dw.dim_date(full_date),
    stage_name             VARCHAR(50) REFERENCES dw.dim_stage(stage_name),
    channel_name           VARCHAR(100) REFERENCES dw.dim_channel(channel_name),
    information_name       VARCHAR(150) REFERENCES dw.dim_information(information_name),
    machine_name           VARCHAR(50) REFERENCES dw.dim_machine(machine_name),
    department_name        VARCHAR(100) REFERENCES dw.dim_department(department_name),
    segment_name           VARCHAR(100) REFERENCES dw.dim_customer_segment(segment_name),
    campaign_name          VARCHAR(150) REFERENCES dw.dim_campaign(campaign_name),
    branch_name            VARCHAR(100) REFERENCES dw.dim_branch(branch_name),
    product_name           VARCHAR(150) REFERENCES dw.dim_product(product_name),

    -- Core sales metrics.
    quantity               NUMERIC(18,2),
    revenue                NUMERIC(18,2) NOT NULL,
    cost                   NUMERIC(18,2),
    profit                 NUMERIC(18,2),
    profit_margin          NUMERIC(18,6),

    -- Operational and funnel proxy metrics.
    inventory_level        NUMERIC(18,2),
    calls                  NUMERIC(18,2),
    waiting_time           NUMERIC(18,2),
    conversion_proxy       NUMERIC(18,6),

    -- Budget, target, and marketing effectiveness metrics.
    budget                 NUMERIC(18,2),
    target                 NUMERIC(18,2),
    marketing_cost         NUMERIC(18,2),
    roi_marketing          NUMERIC(18,6),

    -- Cost breakdown retained from source for richer analysis.
    raw_material_cost      NUMERIC(18,2),
    labor_cost             NUMERIC(18,2),
    logistics_cost         NUMERIC(18,2),
    unit_cost              NUMERIC(18,6),
    revenue_per_unit       NUMERIC(18,6),
    cost_per_machine_unit  NUMERIC(18,6),

    -- Market metrics.
    market_size            NUMERIC(18,2),
    market_share           NUMERIC(18,6),
    region_profit_share    NUMERIC(18,6),

    -- Calculated columns for dashboard logic.
    target_gap             NUMERIC(18,2)
        GENERATED ALWAYS AS (COALESCE(revenue, 0) - COALESCE(target, 0)) STORED,
    target_achievement_rate NUMERIC(18,6)
        GENERATED ALWAYS AS (
            CASE
                WHEN target IS NULL OR target = 0 THEN NULL
                ELSE revenue / target
            END
        ) STORED,
    roi_marketing_calc     NUMERIC(18,6)
        GENERATED ALWAYS AS (
            CASE
                WHEN budget IS NULL OR budget = 0 THEN NULL
                ELSE profit / budget
            END
        ) STORED,

    created_at             TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================
-- FACT 2: CHI PHÍ QUẢNG CÁO (nguồn Facebook Ads CSV)
-- Grain: 1 dòng = 1 ngày x 1 chiến dịch. Dùng chung dim_date,
-- dim_campaign, dim_channel với fact_marketing_sales
-- (conformed dimensions - mô hình fact constellation).
-- ============================================================

CREATE TABLE dw.fact_ad_spend (
    full_date      DATE NOT NULL REFERENCES dw.dim_date(full_date),
    campaign_name  VARCHAR(150) NOT NULL REFERENCES dw.dim_campaign(campaign_name),
    channel_name   VARCHAR(100) REFERENCES dw.dim_channel(channel_name),

    spend          NUMERIC(18,2) NOT NULL,
    impressions    NUMERIC(18,0),
    clicks         NUMERIC(18,0),
    conversions    NUMERIC(18,0),

    -- Chỉ số dẫn xuất cho dashboard.
    ctr            NUMERIC(18,6)
        GENERATED ALWAYS AS (
            CASE WHEN impressions IS NULL OR impressions = 0 THEN NULL
                 ELSE clicks / impressions END
        ) STORED,
    cost_per_click NUMERIC(18,6)
        GENERATED ALWAYS AS (
            CASE WHEN clicks IS NULL OR clicks = 0 THEN NULL
                 ELSE spend / clicks END
        ) STORED,

    created_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (full_date, campaign_name)
);

-- ============================================================
-- FACT 3: THỜI TIẾT THEO NGÀY x VÙNG (nguồn Open-Meteo API)
-- Dùng chung dim_date, dim_region với fact bán hàng.
-- ============================================================

CREATE TABLE dw.fact_weather_daily (
    full_date    DATE NOT NULL REFERENCES dw.dim_date(full_date),
    region_name  VARCHAR(50) NOT NULL REFERENCES dw.dim_region(region_name),
    temp_mean    NUMERIC(6,2),
    temp_max     NUMERIC(6,2),
    rain_mm      NUMERIC(8,2),
    PRIMARY KEY (full_date, region_name)
);

-- ============================================================
-- VIEW: bán hàng + thời tiết (join sẵn cho Tableau)
-- ============================================================

CREATE VIEW dw.v_sales_weather AS
SELECT
    f.*,
    b.region_name,
    p.category_name,
    w.temp_mean,
    w.temp_max,
    w.rain_mm
FROM dw.fact_marketing_sales f
LEFT JOIN dw.dim_branch b ON b.branch_name = f.branch_name
LEFT JOIN dw.dim_product p ON p.product_name = f.product_name
LEFT JOIN dw.fact_weather_daily w
       ON w.full_date = f.full_date
      AND w.region_name = b.region_name;

-- ============================================================
-- INDEXES cho truy vấn dashboard
-- ============================================================

CREATE INDEX idx_fact_sales_date     ON dw.fact_marketing_sales (full_date);
CREATE INDEX idx_fact_sales_channel  ON dw.fact_marketing_sales (channel_name);
CREATE INDEX idx_fact_sales_campaign ON dw.fact_marketing_sales (campaign_name);
CREATE INDEX idx_fact_sales_branch   ON dw.fact_marketing_sales (branch_name);
CREATE INDEX idx_fact_sales_product  ON dw.fact_marketing_sales (product_name);
CREATE INDEX idx_fact_ads_campaign   ON dw.fact_ad_spend (campaign_name);
