"""
app.py — VNRetail BI Pipeline UI
Streamlit app: upload Excel → validate → run ETL → show results
"""

import os
import subprocess
import shutil
from datetime import datetime

import pandas as pd
import streamlit as st

# ── Cấu hình ──────────────────────────────────────────────────────────────────
APP_DIR    = os.path.dirname(os.path.abspath(__file__))
DATA_DIR   = os.path.join(APP_DIR, "data")
TARGET     = os.path.join(DATA_DIR, "vnretail_data.xlsx")
ETL_SCRIPT = os.path.join(APP_DIR, "run_etl.sh")

VALID_CATEGORIES = {'Bia', 'Gia vị', 'Mì ăn liền', 'Nước giải khát', 'Snack', 'Thực phẩm', 'Đồ uống'}
VALID_REGIONS    = {'Miền Bắc', 'Miền Trung', 'Miền Nam'}
VALID_SEGMENTS   = {'Bán lẻ', 'Kênh hiện đại', 'Nhà phân phối', 'Thương mại điện tử'}
REQUIRED_COLS    = ['OrderID', 'Date', 'Region', 'Product', 'Category',
                    'Quantity', 'Revenue', 'Cost', 'Profit']

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="VNRetail BI — Data Pipeline",
    page_icon="assets/favicon.png" if os.path.exists("assets/favicon.png") else "📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ─────────────────────────────────────────────────────────────────
st.markdown("""
<style>
/* ── Fonts & base ── */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}

/* ── Hide Streamlit chrome ── */
#MainMenu, footer, header { visibility: hidden; }
.stDeployButton { display: none; }

/* ── Top header bar ── */
.top-header {
    background: linear-gradient(135deg, #0f172a 0%, #1e3a5f 100%);
    color: white;
    padding: 20px 32px;
    border-radius: 12px;
    margin-bottom: 28px;
    display: flex;
    align-items: center;
    justify-content: space-between;
}
.top-header h1 {
    font-size: 22px;
    font-weight: 700;
    margin: 0;
    letter-spacing: -0.3px;
}
.top-header span {
    font-size: 13px;
    opacity: 0.65;
    font-weight: 400;
}
.badge {
    background: rgba(255,255,255,0.12);
    border: 1px solid rgba(255,255,255,0.2);
    color: white;
    padding: 4px 12px;
    border-radius: 20px;
    font-size: 12px;
    font-weight: 500;
}

/* ── Step cards ── */
.step-card {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 10px;
    padding: 20px 24px;
    margin-bottom: 20px;
}
.step-label {
    font-size: 11px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 1px;
    color: #64748b;
    margin-bottom: 6px;
}
.step-title {
    font-size: 16px;
    font-weight: 600;
    color: #0f172a;
    margin-bottom: 16px;
}

/* ── Stat cards ── */
.stat-row { display: flex; gap: 14px; margin: 16px 0; }
.stat-card {
    flex: 1;
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    padding: 14px 18px;
}
.stat-card.error  { border-left: 3px solid #ef4444; background: #fff5f5; }
.stat-card.warn   { border-left: 3px solid #f59e0b; background: #fffbeb; }
.stat-card.ok     { border-left: 3px solid #10b981; background: #f0fdf4; }
.stat-card.info   { border-left: 3px solid #3b82f6; background: #eff6ff; }
.stat-label { font-size: 11px; color: #64748b; font-weight: 500; margin-bottom: 4px; }
.stat-value { font-size: 24px; font-weight: 700; color: #0f172a; }
.stat-sub   { font-size: 12px; color: #94a3b8; margin-top: 2px; }

/* ── Status pill ── */
.pill-pass { background:#dcfce7; color:#16a34a; padding:3px 10px; border-radius:12px; font-size:12px; font-weight:600; }
.pill-fail { background:#fee2e2; color:#dc2626; padding:3px 10px; border-radius:12px; font-size:12px; font-weight:600; }
.pill-warn { background:#fef3c7; color:#d97706; padding:3px 10px; border-radius:12px; font-size:12px; font-weight:600; }

/* ── Table ── */
.styled-table { width:100%; border-collapse:collapse; font-size:13px; }
.styled-table th {
    background:#f1f5f9; color:#475569;
    font-weight:600; font-size:11px; text-transform:uppercase;
    letter-spacing:0.5px; padding:10px 14px; text-align:left;
    border-bottom:1px solid #e2e8f0;
}
.styled-table td { padding:10px 14px; border-bottom:1px solid #f1f5f9; color:#334155; }
.styled-table tr:last-child td { border-bottom:none; }
.styled-table tr:hover td { background:#f8fafc; }

/* ── DB connection block ── */
.db-block {
    background: #0f172a;
    color: #94a3b8;
    border-radius: 8px;
    padding: 12px 16px;
    font-family: 'Courier New', monospace;
    font-size: 12px;
    line-height: 1.8;
}
.db-block .key { color: #64748b; }
.db-block .val { color: #e2e8f0; font-weight: 600; }

/* ── Sidebar ── */
section[data-testid="stSidebar"] {
    background: #f8fafc;
    border-right: 1px solid #e2e8f0;
}
section[data-testid="stSidebar"] .sidebar-logo {
    font-size: 18px; font-weight: 700; color: #0f172a;
    padding: 8px 0 20px 0; border-bottom: 1px solid #e2e8f0; margin-bottom: 20px;
}

/* ── Primary button override ── */
.stButton > button[kind="primary"] {
    background: #1e40af;
    border: none;
    border-radius: 8px;
    font-weight: 600;
    letter-spacing: 0.2px;
    padding: 10px 24px;
    transition: background 0.15s;
}
.stButton > button[kind="primary"]:hover { background: #1d4ed8; }

/* ── File uploader ── */
[data-testid="stFileUploader"] {
    border: 2px dashed #cbd5e1;
    border-radius: 10px;
    background: #f8fafc;
    padding: 8px;
}

/* ── Divider ── */
hr { border-color: #e2e8f0; margin: 20px 0; }

/* ── Log output ── */
.log-box {
    background: #0f172a;
    color: #94a3b8;
    border-radius: 8px;
    padding: 14px 16px;
    font-family: monospace;
    font-size: 12px;
    line-height: 1.7;
    max-height: 300px;
    overflow-y: auto;
}
.log-ok   { color: #34d399; }
.log-err  { color: #f87171; }
.log-info { color: #60a5fa; }
</style>
""", unsafe_allow_html=True)

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="top-header">
  <div>
    <div class="step-label" style="color:rgba(255,255,255,0.5);margin-bottom:4px;">VNRetail Group</div>
    <h1>BI Data Pipeline</h1>
    <span>Upload → Validate → Load to Data Warehouse</span>
  </div>
  <span class="badge">PostgreSQL · DW Schema</span>
</div>
""", unsafe_allow_html=True)

# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown('<div class="sidebar-logo">VNRetail BI</div>', unsafe_allow_html=True)

    st.markdown("**Trạng thái dữ liệu**")
    if os.path.exists(TARGET):
        mtime = datetime.fromtimestamp(os.path.getmtime(TARGET))
        try:
            df_cur = pd.read_excel(TARGET, usecols=['Date', 'Revenue'])
            total_rev = df_cur['Revenue'].sum() / 1e6
            n_records = len(df_cur)
        except:
            total_rev, n_records = None, None

        st.markdown(f"""
        <div class="stat-card ok" style="margin-bottom:10px;">
            <div class="stat-label">File hiện tại</div>
            <div style="font-size:13px;font-weight:600;color:#0f172a;">vnretail_data.xlsx</div>
            <div class="stat-sub">Cập nhật {mtime.strftime('%d/%m/%Y %H:%M')}</div>
        </div>
        """, unsafe_allow_html=True)

        if n_records:
            c1, c2 = st.columns(2)
            c1.metric("Bản ghi", f"{n_records:,}")
            if total_rev:
                c2.metric("Doanh thu", f"{total_rev:.1f} tỷ")
    else:
        st.markdown("""
        <div class="stat-card warn">
            <div class="stat-label">File dữ liệu</div>
            <div style="font-size:13px;color:#92400e;">Chưa có file data</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<hr>", unsafe_allow_html=True)
    st.markdown("**Kết nối Database**")
    st.markdown("""
    <div class="db-block">
      <span class="key">host  </span><span class="val">localhost:5434</span><br>
      <span class="key">db    </span><span class="val">bi_db</span><br>
      <span class="key">schema</span><span class="val">dw</span><br>
      <span class="key">user  </span><span class="val">bi_user</span>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<hr>", unsafe_allow_html=True)
    st.markdown("**Quy trình**", unsafe_allow_html=True)
    st.markdown("""
    <div style="font-size:13px;color:#475569;line-height:2;">
    1&nbsp;&nbsp;Upload file Excel<br>
    2&nbsp;&nbsp;Kiểm tra chất lượng<br>
    3&nbsp;&nbsp;Nạp vào Data Warehouse
    </div>
    """, unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
# STEP 1 — Upload
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown("""
<div class="step-card">
  <div class="step-label">Bước 1</div>
  <div class="step-title">Chọn file dữ liệu</div>
""", unsafe_allow_html=True)

uploaded = st.file_uploader(
    "Kéo thả hoặc chọn file .xlsx",
    type=["xlsx"],
    label_visibility="collapsed",
    help="Yêu cầu các cột: " + ", ".join(REQUIRED_COLS),
)
st.markdown("</div>", unsafe_allow_html=True)

if not uploaded:
    st.markdown("""
    <div style="text-align:center;padding:40px 0;color:#94a3b8;font-size:14px;">
        Chưa có file nào được chọn. Kéo thả file Excel vào ô phía trên.
    </div>
    """, unsafe_allow_html=True)
    st.stop()

# Đọc file
try:
    df = pd.read_excel(uploaded)
except Exception as e:
    st.error(f"Không đọc được file: {e}")
    st.stop()

# File summary
col_a, col_b, col_c = st.columns(3)
col_a.metric("Tên file", uploaded.name)
col_b.metric("Số bản ghi", f"{len(df):,}")
col_c.metric("Số cột", len(df.columns))

with st.expander("Xem trước dữ liệu (10 dòng đầu)"):
    st.dataframe(df.head(10), use_container_width=True, hide_index=True)

# ═══════════════════════════════════════════════════════════════════════════════
# STEP 2 — Validate
# ═══════════════════════════════════════════════════════════════════════════════
def validate(df: pd.DataFrame):
    """
    Trả về:
      hard_errors : list[dict]  — lỗi cấu trúc, phải sửa file
      row_errors  : list[dict]  — lỗi từng dòng, có thể tự lọc
      warnings    : list[dict]  — cảnh báo mềm
      bad_rows    : set[int]    — tập index các dòng lỗi
    """
    hard_errors, row_errors, warnings = [], [], []
    bad_rows: set = set()

    # 1. Cột bắt buộc — hard error
    missing_cols = [c for c in REQUIRED_COLS if c not in df.columns]
    if missing_cols:
        hard_errors.append({
            "Kiểm tra": "Cột bắt buộc",
            "Chi tiết": f"Thiếu cột: {', '.join(missing_cols)}",
            "Số dòng": "Toàn bộ file — phải sửa file",
        })
        return hard_errors, row_errors, warnings, bad_rows

    total = len(df)

    # 2. Date format
    bad_date = pd.to_datetime(df['Date'], format='%Y-%m-%d', errors='coerce').isna() & df['Date'].notna()
    if bad_date.sum():
        idx = df.index[bad_date].tolist()
        bad_rows.update(idx)
        row_errors.append({
            "Kiểm tra": "Định dạng Date",
            "Chi tiết": f"Phải là YYYY-MM-DD. Ví dụ sai: {df.loc[bad_date,'Date'].iloc[0]}",
            "Số dòng": f"{bad_date.sum():,}",
            "Dòng đầu": str((bad_date.index[bad_date] + 2).tolist()[:5])[1:-1],
        })

    # 3. Null ở cột bắt buộc
    for col in REQUIRED_COLS:
        nm = df[col].isna()
        if nm.sum():
            idx = df.index[nm].tolist()
            bad_rows.update(idx)
            row_errors.append({
                "Kiểm tra": f"Giá trị rỗng — {col}",
                "Chi tiết": f"Cột '{col}' không được để trống",
                "Số dòng": f"{nm.sum():,}",
                "Dòng đầu": str((df.index[nm] + 2).tolist()[:5])[1:-1],
            })

    # 4. Revenue
    rev = pd.to_numeric(df['Revenue'], errors='coerce')
    non_num = df['Revenue'].notna() & rev.isna()
    if non_num.sum():
        idx = df.index[non_num].tolist()
        bad_rows.update(idx)
        row_errors.append({
            "Kiểm tra": "Revenue — không phải số",
            "Chi tiết": f"Ví dụ: {df.loc[non_num,'Revenue'].iloc[:3].tolist()}",
            "Số dòng": f"{non_num.sum():,}",
            "Dòng đầu": str((df.index[non_num] + 2).tolist()[:5])[1:-1],
        })
    neg_rev = rev.notna() & (rev <= 0)
    if neg_rev.sum():
        idx = df.index[neg_rev].tolist()
        bad_rows.update(idx)
        row_errors.append({
            "Kiểm tra": "Revenue — âm hoặc = 0",
            "Chi tiết": "Revenue phải > 0",
            "Số dòng": f"{neg_rev.sum():,}",
            "Dòng đầu": str((df.index[neg_rev] + 2).tolist()[:5])[1:-1],
        })

    # 5. Quantity
    qty = pd.to_numeric(df['Quantity'], errors='coerce')
    bad_qty = qty.notna() & (qty <= 0)
    if bad_qty.sum():
        idx = df.index[bad_qty].tolist()
        bad_rows.update(idx)
        row_errors.append({
            "Kiểm tra": "Quantity ≤ 0",
            "Chi tiết": "Phải là số nguyên dương",
            "Số dòng": f"{bad_qty.sum():,}",
            "Dòng đầu": str((df.index[bad_qty] + 2).tolist()[:5])[1:-1],
        })

    # 6. Category
    nonnull_cat = df[df['Category'].notna()]
    bad_cat = ~nonnull_cat['Category'].isin(VALID_CATEGORIES)
    if bad_cat.sum():
        idx = nonnull_cat.index[bad_cat].tolist()
        bad_rows.update(idx)
        row_errors.append({
            "Kiểm tra": "Category không hợp lệ",
            "Chi tiết": f"Giá trị sai: {nonnull_cat.loc[bad_cat,'Category'].unique()[:5].tolist()}",
            "Số dòng": f"{bad_cat.sum():,}",
            "Dòng đầu": str(([i + 2 for i in idx])[:5])[1:-1],
        })

    # 7. Region
    nonnull_reg = df[df['Region'].notna()]
    bad_reg = ~nonnull_reg['Region'].isin(VALID_REGIONS)
    if bad_reg.sum():
        idx = nonnull_reg.index[bad_reg].tolist()
        bad_rows.update(idx)
        row_errors.append({
            "Kiểm tra": "Region không hợp lệ",
            "Chi tiết": f"Giá trị sai: {nonnull_reg.loc[bad_reg,'Region'].unique()[:5].tolist()}",
            "Số dòng": f"{bad_reg.sum():,}",
            "Dòng đầu": str(([i + 2 for i in idx])[:5])[1:-1],
        })

    # ── Cảnh báo (không track bad_rows) ──
    if 'CustomerSegment' in df.columns:
        bad_seg = ~df['CustomerSegment'].isin(VALID_SEGMENTS) & df['CustomerSegment'].notna()
        if bad_seg.sum():
            warnings.append({
                "Kiểm tra": "CustomerSegment lạ",
                "Chi tiết": f"Giá trị: {df.loc[bad_seg,'CustomerSegment'].unique()[:5].tolist()}",
                "Số dòng": f"{bad_seg.sum():,}",
            })

    cost_num = pd.to_numeric(df['Cost'], errors='coerce')
    loss = (rev < cost_num) & rev.notna() & cost_num.notna()
    if loss.sum():
        warnings.append({
            "Kiểm tra": "Revenue < Cost (lỗ)",
            "Chi tiết": "Nên kiểm tra lại chính sách giá",
            "Số dòng": f"{loss.sum():,} ({loss.sum()/total*100:.1f}%)",
        })

    dup = df['OrderID'].duplicated().sum()
    if dup:
        warnings.append({
            "Kiểm tra": "Trùng OrderID",
            "Chi tiết": "OrderID xuất hiện nhiều hơn 1 lần",
            "Số dòng": f"{dup:,}",
        })

    return hard_errors, row_errors, warnings, bad_rows


def render_table(rows: list):
    if not rows:
        return
    tdf = pd.DataFrame(rows)
    html = '<table class="styled-table"><thead><tr>'
    for c in tdf.columns:
        html += f'<th>{c}</th>'
    html += '</tr></thead><tbody>'
    for _, row in tdf.iterrows():
        html += '<tr>' + ''.join(f'<td>{v}</td>' for v in row) + '</tr>'
    html += '</tbody></table>'
    st.markdown(html, unsafe_allow_html=True)


with st.spinner("Đang kiểm tra dữ liệu..."):
    hard_errors, row_errors, warnings, bad_rows = validate(df)

n_bad   = len(bad_rows)
n_clean = len(df) - n_bad
has_errors = bool(hard_errors or row_errors)

# ── Tổng kết validation ──
st.markdown("""
<div class="step-card">
  <div class="step-label">Bước 2</div>
  <div class="step-title">Kết quả kiểm tra chất lượng</div>
""", unsafe_allow_html=True)

err_class  = "error" if has_errors else "ok"
warn_class = "warn"  if warnings   else "ok"

st.markdown(f"""
<div class="stat-row">
  <div class="stat-card info">
    <div class="stat-label">Tổng bản ghi</div>
    <div class="stat-value">{len(df):,}</div>
    <div class="stat-sub">{len(df.columns)} cột</div>
  </div>
  <div class="stat-card {'error' if n_bad else 'ok'}">
    <div class="stat-label">Bản ghi lỗi</div>
    <div class="stat-value">{n_bad:,}</div>
    <div class="stat-sub">{'Có thể tự lọc bỏ' if row_errors and not hard_errors else ('Phải sửa file' if hard_errors else 'Không có lỗi')}</div>
  </div>
  <div class="stat-card {'ok' if n_bad == 0 else 'info'}">
    <div class="stat-label">Bản ghi hợp lệ</div>
    <div class="stat-value">{n_clean:,}</div>
    <div class="stat-sub">{f'{n_clean/len(df)*100:.1f}% tổng file' if len(df) else ''}</div>
  </div>
  <div class="stat-card {warn_class}">
    <div class="stat-label">Cảnh báo</div>
    <div class="stat-value">{len(warnings)}</div>
    <div class="stat-sub">{'Nên xem lại' if warnings else 'Không có'}</div>
  </div>
</div>
""", unsafe_allow_html=True)

# ── Hard errors ──
if hard_errors:
    st.markdown("**Lỗi cấu trúc — bắt buộc sửa file trước khi nạp**")
    render_table(hard_errors)

# ── Row-level errors ──
if row_errors:
    st.markdown(f"**Chi tiết {len(row_errors)} loại lỗi dữ liệu ({n_bad:,} dòng)**")
    render_table(row_errors)

    if not hard_errors:
        # Cho phép lọc tự động
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown(f"""
        <div style="background:#eff6ff;border:1px solid #bfdbfe;border-radius:8px;
                    padding:14px 18px;font-size:13px;color:#1e40af;">
          <strong>Tùy chọn xử lý lỗi:</strong><br>
          Hệ thống phát hiện <strong>{n_bad:,} bản ghi lỗi</strong>.
          Bạn có thể tự động lọc bỏ các dòng này và nạp <strong>{n_clean:,} bản ghi hợp lệ</strong> còn lại,
          hoặc tải xuống file lỗi để sửa thủ công.
        </div>
        """, unsafe_allow_html=True)

        col_opt1, col_opt2 = st.columns(2)
        with col_opt1:
            auto_filter = st.checkbox(
                f"Tự động lọc bỏ {n_bad:,} dòng lỗi — nạp {n_clean:,} dòng hợp lệ",
                value=False,
            )
        with col_opt2:
            # Tải xuống file lỗi để sửa
            bad_df = df.iloc[sorted(bad_rows)].copy()
            import io as _io
            buf = _io.BytesIO()
            bad_df.to_excel(buf, index=False)
            st.download_button(
                label=f"Tải xuống {n_bad:,} dòng lỗi (.xlsx)",
                data=buf.getvalue(),
                file_name=f"error_rows_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )

        if auto_filter:
            df_clean = df.drop(index=sorted(bad_rows)).reset_index(drop=True)
            st.success(f"Sẽ nạp {len(df_clean):,} bản ghi hợp lệ (bỏ qua {n_bad:,} dòng lỗi)")
            with st.expander("Xem trước dữ liệu sau lọc (10 dòng đầu)"):
                st.dataframe(df_clean.head(10), use_container_width=True, hide_index=True)
        else:
            df_clean = None
    else:
        df_clean = None
else:
    df_clean = df.copy()

# ── Cảnh báo ──
if warnings:
    with st.expander(f"Xem {len(warnings)} cảnh báo"):
        render_table(warnings)

if not has_errors:
    st.success("Dữ liệu hợp lệ — sẵn sàng nạp vào Data Warehouse")

st.markdown("</div>", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
# STEP 3 — ETL
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown("""
<div class="step-card">
  <div class="step-label">Bước 3</div>
  <div class="step-title">Nạp vào Data Warehouse</div>
""", unsafe_allow_html=True)

# Block nếu hard error hoặc có lỗi dòng mà chưa chọn lọc
if hard_errors:
    st.warning("Phải sửa lỗi cấu trúc ở Bước 2 trước khi tiếp tục.")
    st.markdown("</div>", unsafe_allow_html=True)
    st.stop()

if row_errors and df_clean is None:
    st.warning("Vui lòng chọn cách xử lý lỗi ở Bước 2 trước khi chạy ETL.")
    st.markdown("</div>", unsafe_allow_html=True)
    st.stop()

n_to_load = len(df_clean)
backup_ts = datetime.now().strftime('%Y%m%d_%H%M')
st.markdown(f"""
<div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;padding:14px 18px;
            font-size:13px;color:#475569;line-height:2;margin-bottom:16px;">
  <strong style="color:#0f172a;">Các bước sẽ được thực hiện:</strong><br>
  1. Backup file hiện tại → <code>vnretail_data_backup_{backup_ts}.xlsx</code><br>
  2. Lưu <strong>{n_to_load:,} bản ghi</strong> vào <code>vnretail_data.xlsx</code>
     {'(đã lọc bỏ ' + str(n_bad) + ' dòng lỗi)' if n_bad else ''}<br>
  3. Chạy ETL pipeline: Excel → staging → DW (PostgreSQL)<br>
  4. Cập nhật dữ liệu thời tiết từ API
</div>
""", unsafe_allow_html=True)

run_col, _ = st.columns([1, 4])
run_btn = run_col.button("Chạy ETL Pipeline", type="primary", use_container_width=True)

if run_btn:
    progress = st.progress(0)
    status   = st.empty()
    log_box  = st.empty()
    logs     = []

    def log(msg, kind="info"):
        prefix = {"ok": "✓", "err": "✗", "info": "→"}.get(kind, "→")
        logs.append(f"{prefix}  {msg}")
        log_box.markdown(
            '<div class="log-box">' +
            "<br>".join(
                f'<span class="log-{("ok" if l.startswith("✓") else "err" if l.startswith("✗") else "info")}">{l}</span>'
                for l in logs[-25:]
            ) +
            "</div>",
            unsafe_allow_html=True,
        )

    # Backup
    progress.progress(10)
    status.markdown("**Đang backup file cũ...**")
    if os.path.exists(TARGET):
        backup_name = f"vnretail_data_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        shutil.copy(TARGET, os.path.join(DATA_DIR, backup_name))
        log(f"Backup xong → {backup_name}", "ok")
    else:
        log("Không có file cũ — bỏ qua backup", "info")

    # Ghi file (df_clean có thể là subset đã lọc)
    progress.progress(20)
    status.markdown("**Đang lưu file...**")
    df_clean.to_excel(TARGET, index=False)
    if n_bad:
        log(f"Đã lưu {n_to_load:,} bản ghi hợp lệ (lọc bỏ {n_bad:,} dòng lỗi)", "ok")
    else:
        log(f"Đã lưu {n_to_load:,} bản ghi vào vnretail_data.xlsx", "ok")

    # Chạy ETL
    progress.progress(30)
    status.markdown("**Đang chạy ETL pipeline...**")
    log("Bắt đầu run_etl.sh", "info")

    try:
        result = subprocess.run(
            ["bash", ETL_SCRIPT],
            capture_output=True,
            text=True,
            cwd=APP_DIR,
            timeout=300,
        )
        progress.progress(90)

        for line in (result.stdout + result.stderr).split('\n'):
            if line.strip():
                log(line.strip(), "info")

        if result.returncode == 0:
            progress.progress(100)
            status.empty()
            log("ETL hoàn thành thành công", "ok")

            st.markdown(f"""
            <div style="background:#f0fdf4;border:1px solid #bbf7d0;border-radius:8px;
                        padding:16px 20px;margin-top:16px;">
              <div style="font-weight:600;color:#15803d;font-size:15px;margin-bottom:8px;">
                ETL hoàn thành
              </div>
              <div style="font-size:13px;color:#166534;line-height:2;">
                <strong>{n_to_load:,} bản ghi</strong> đã được nạp vào Data Warehouse
                {'<br><span style="color:#6b7280;">(' + str(n_bad) + ' dòng lỗi đã được lọc bỏ)</span>' if n_bad else ''}<br>
                Schema: <code>dw</code> &nbsp;|&nbsp; DB: <code>bi_db</code> &nbsp;|&nbsp; Port: <code>5434</code><br>
                Tiếp theo: mở Tableau và nhấn <strong>F5</strong> để refresh dashboard
              </div>
            </div>
            """, unsafe_allow_html=True)
        else:
            progress.progress(100)
            status.empty()
            log("ETL kết thúc với lỗi", "err")
            st.error("ETL gặp lỗi. Xem log bên dưới.")
            if result.stderr:
                st.code(result.stderr[-2000:])

    except subprocess.TimeoutExpired:
        st.error("ETL timeout (> 5 phút). Kiểm tra Docker/PostgreSQL đang chạy.")
    except FileNotFoundError:
        st.error(f"Không tìm thấy run_etl.sh tại: {ETL_SCRIPT}")
    except Exception as e:
        st.error(f"Lỗi không xác định: {e}")

    with st.expander("Xem toàn bộ log"):
        st.code("\n".join(logs))

st.markdown("</div>", unsafe_allow_html=True)
