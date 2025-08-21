# -*- coding: utf-8 -*-
import io
import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="财务仪表板 Demo（AP账龄 + 费用分析）", layout="wide")
st.title("财务仪表板 Demo（AP 账龄 + 费用分析）")
st.caption("上传三张 CSV（expenses / ap_invoices / vendors），或直接使用示例数据。支持筛选、动态图表、异常导出。")

# ------------------ 示例数据 ------------------
def sample_expenses():
    csv = """Date,Dept,Category,VendorCode,Amount
2025-01-05,Sales,Travel,V0001,1200
2025-01-14,Sales,Meals,V0001,320
2025-02-02,IT,Software,V0003,5600
2025-02-18,Finance,Training,V0002,1800
2025-03-03,Sales,Travel,V0001,1500
2025-03-20,IT,Hardware,V0004,7200
2025-04-08,Finance,Office,V0005,900
2025-04-28,Sales,Marketing,V0006,4200
2025-05-11,IT,Software,V0003,6100
2025-06-05,Finance,Office,V0005,1300
"""
    return pd.read_csv(io.StringIO(csv), parse_dates=["Date"])

def sample_ap_invoices():
    csv = """InvoiceID,VendorCode,InvoiceDate,DueDate,Amount,PaidAmount
INV001,V0001,2025-01-10,2025-02-09,10000,10000
INV002,V0001,2025-01-25,2025-02-24,5000,4800
INV010,V0002,2025-02-01,2025-03-03,8000,0
INV021,V0003,2025-03-05,2025-03-25,12000,3000
INV035,V0004,2025-03-15,2025-04-14,4500,0
INV050,V0005,2025-04-10,2025-05-10,2600,1000
INV066,V0006,2025-04-20,2025-05-20,7000,7000
INV077,V0003,2025-05-01,2025-06-01,5600,0
INV088,V0005,2025-06-05,2025-07-05,1300,0
"""
    return pd.read_csv(io.StringIO(csv), parse_dates=["InvoiceDate","DueDate"])

def sample_vendors():
    csv = """VendorCode,VendorName,Region
V0001,Tokyo Supplies,JP
V0002,Osaka Service,JP
V0003,Sapporo Tech,JP
V0004,Hangzhou Parts,CN
V0005,Hangzhou Office,CN
V0006,Shanghai Media,CN
"""
    return pd.read_csv(io.StringIO(csv))

def to_excel_bytes(sheets: dict):
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="xlsxwriter") as writer:
        for name, df in sheets.items():
            df.to_excel(writer, index=False, sheet_name=name[:31] or "Sheet1")
    return buf.getvalue()

# ------------------ 侧边栏：上传 / 下载示例 ------------------
with st.sidebar:
    st.header("数据源")
    exp_file = st.file_uploader("上传 expenses.csv", type=["csv"])
    ap_file  = st.file_uploader("上传 ap_invoices.csv", type=["csv"])
    ven_file = st.file_uploader("上传 vendors.csv", type=["csv"])
    st.markdown("---")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.download_button("示例-费用", data=sample_expenses().to_csv(index=False).encode("utf-8-sig"),
                           file_name="expenses.csv", mime="text/csv")
    with c2:
        st.download_button("示例-应付", data=sample_ap_invoices().to_csv(index=False).encode("utf-8-sig"),
                           file_name="ap_invoices.csv", mime="text/csv")
    with c3:
        st.download_button("示例-供应商", data=sample_vendors().to_csv(index=False).encode("utf-8-sig"),
                           file_name="vendors.csv", mime="text/csv")

# ------------------ 读取数据（无上传则用示例） ------------------
def read_csv_or_sample(uf, fallback_fn, parse_dates=None):
    if uf is None:
        return fallback_fn()
    return pd.read_csv(uf, parse_dates=parse_dates)

expenses = read_csv_or_sample(exp_file, sample_expenses, parse_dates=["Date"])
ap = read_csv_or_sample(ap_file, sample_ap_invoices, parse_dates=["InvoiceDate","DueDate"])
vendors = read_csv_or_sample(ven_file, sample_vendors)

# 规范字段
for df in (expenses, ap, vendors):
    if "VendorCode" in df.columns:
        df["VendorCode"] = df["VendorCode"].astype(str).str.upper().str.strip()

# join 供应商信息
expenses = expenses.merge(vendors, on="VendorCode", how="left")
ap = ap.merge(vendors, on="VendorCode", how="left")

# ------------------ 派生字段 / 账龄 ------------------
ap["Outstanding"] = (pd.to_numeric(ap["Amount"], errors="coerce").fillna(0)
                     - pd.to_numeric(ap["PaidAmount"], errors="coerce").fillna(0))
ap["DaysPastDue"] = (pd.to_datetime("today").normalize() - pd.to_datetime(ap["DueDate"])).dt.days
ap["DaysPastDue"] = ap["DaysPastDue"].fillna(0).astype(int)

def bucketize(d):
    if d <= 0: return "Not Due"
    if d <= 30: return "1-30"
    if d <= 60: return "31-60"
    if d <= 90: return "61-90"
    return "90+"
ap["AgingBucket"] = ap["DaysPastDue"].apply(bucketize)

# ------------------ 顶部筛选 ------------------
min_date = min(expenses["Date"].min(), ap["InvoiceDate"].min())
max_date = max(expenses["Date"].max(), ap["InvoiceDate"].max())
fd1, fd2, fd3, fd4 = st.columns([1.3,1,1,1])
with fd1:
    dr = st.date_input("日期范围（按费用Date）", (min_date, max_date))
with fd2:
    dept = st.multiselect("部门", sorted(expenses["Dept"].dropna().unique().tolist()))
with fd3:
    cat = st.multiselect("费用类别", sorted(expenses["Category"].dropna().unique().tolist()))
with fd4:
    reg = st.multiselect("区域", sorted(vendors["Region"].dropna().unique().tolist()))

# 应用筛选到费用与应付
def apply_filters(df_exp, df_ap):
    e = df_exp.copy()
    a = df_ap.copy()
    if isinstance(dr, (list, tuple)) and len(dr) == 2:
        e = e[(e["Date"] >= pd.to_datetime(dr[0])) & (e["Date"] <= pd.to_datetime(dr[1]))]
    if dept:
        e = e[e["Dept"].isin(dept)]
    if cat:
        e = e[e["Category"].isin(cat)]
    if reg:
        e = e[e["Region"].isin(reg)]
        a = a[a["Region"].isin(reg)]
    return e, a

expenses_f, ap_f = apply_filters(expenses, ap)

# ------------------ KPI 卡片 ------------------
def expense_kpis(e_df):
    total = e_df["Amount"].sum()
    # 月度序列
    s = (e_df.set_index("Date")
             .sort_index()
             .groupby(pd.Grouper(freq="MS"))["Amount"].sum())
    mom = None
    if len(s) >= 2 and s.iloc[-2] != 0:
        mom = (s.iloc[-1] - s.iloc[-2]) / s.iloc[-2]
    return total, mom

total_expense, mom = expense_kpis(expenses_f)
ap_outstanding = ap_f["Outstanding"].sum()
ap_90p = ap_f.loc[ap_f["AgingBucket"] == "90+", "Outstanding"].sum()

k1, k2, k3, k4 = st.columns(4)
k1.metric("Total Expense", f"{total_expense:,.0f}")
k2.metric("Expense MoM %", "-" if mom is None else f"{mom*100:,.1f}%")
k3.metric("AP Outstanding", f"{ap_outstanding:,.0f}")
k4.metric("AP 90+", f"{ap_90p:,.0f}")

st.divider()

# ------------------ 图表区域 ------------------
# 费用趋势（月）
exp_month = (expenses_f.assign(Month=pd.to_datetime(expenses_f["Date"]).dt.to_period("M").dt.to_timestamp())
                        .groupby("Month", as_index=False)["Amount"].sum())
fig1 = px.line(exp_month, x="Month", y="Amount", markers=True, title="费用趋势（月）")

# 供应商未付Top10
ap_vendor = (ap_f.groupby(["VendorCode","VendorName"], as_index=False)["Outstanding"].sum()
               .sort_values("Outstanding", ascending=False).head(10))
fig2 = px.bar(ap_vendor, x="VendorName", y="Outstanding", title="AP Outstanding Top 10 供应商")

# 账龄堆叠（供应商×账龄）
aging_pivot = (ap_f.pivot_table(index="VendorName", columns="AgingBucket",
                                values="Outstanding", aggfunc="sum", fill_value=0)
                 .reset_index())
# 为了可视化，转长表
aging_long = aging_pivot.melt(id_vars="VendorName", var_name="Bucket", value_name="Amount")
fig3 = px.bar(aging_long, x="VendorName", y="Amount", color="Bucket", title="账龄结构（供应商×Bucket）")

# 费用按类别
exp_cat = (expenses_f.groupby("Category", as_index=False)["Amount"].sum()
             .sort_values("Amount", ascending=False))
fig4 = px.pie(exp_cat, names="Category", values="Amount", title="费用结构（类别）")

# 布局展示
g1, g2 = st.columns([1.2,1])
with g1:
    st.plotly_chart(fig1, use_container_width=True)
with g2:
    st.plotly_chart(fig4, use_container_width=True)

g3 = st.container()
with g3:
    st.plotly_chart(fig2, use_container_width=True)
    st.plotly_chart(fig3, use_container_width=True)

# 明细表
st.markdown("### 发票明细")
detail_cols = ["InvoiceID","VendorName","Region","InvoiceDate","DueDate","Amount","PaidAmount","Outstanding","DaysPastDue","AgingBucket"]
st.dataframe(ap_f[detail_cols].sort_values(["AgingBucket","DaysPastDue","Outstanding"], ascending=[True, False, False]),
             use_container_width=True, height=280)

# ------------------ 导出结果 ------------------
st.subheader("下载汇总结果")
export_bytes = to_excel_bytes({
    "Expense_By_Month": exp_month,
    "Expense_By_Category": exp_cat,
    "AP_Vendor_Outstanding": ap_vendor,
    "AP_Aging_Long": aging_long,
    "AP_Detail": ap_f[detail_cols]
})
st.download_button(
    "下载结果包（Excel，多Sheet）",
    data=export_bytes,
    file_name="ap_expense_dashboard.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)
