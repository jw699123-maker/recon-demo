import io
import numpy as np
import pandas as pd
import streamlit as st
import json

# ---------- Page config ----------
st.set_page_config(page_title="对账自动化 Demo（发票×账单）", page_icon="✅", layout="wide")

# 侧边栏：上传 rules.json（可选）
rule_file = st.sidebar.file_uploader("上传 rules.json（可选）", type=["json"])

# 若没有上传，也可以从仓库内置文件读取
def load_rules():
    if rule_file is not None:
        return json.load(rule_file)
    try:
        with open("rules.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return None

rules = load_rules()

# 使用示例：容差
def amounts_equal(a: float, b: float, ccy: str) -> bool:
    """
    根据 rules.json 的容差设置比较金额是否视为相等。
    兼容三种模式：absolute / percent / both。
    """
    # 没有规则时的兜底：四舍五入到 2 位后直接比较
    if not rules or "tolerance" not in rules:
        return round(float(a), 2) == round(float(b), 2)

    tol = rules["tolerance"]  # 注意是 tol，不是 t
    mode = tol.get("mode", "both")

    # 绝对容差（可按币种覆盖）
    abs_tol = float(tol.get("absolute", {}).get("value", 0.0))
    per_ccy = tol.get("absolute", {}).get("per_currency", {}) or {}
    if ccy in per_ccy:
        abs_tol = float(per_ccy[ccy])

    # 百分比容差（写成完整的 if-else 三元表达式，避免 "应为 else" 报错）
    if mode in ("percent", "both"):
        pct_tol = float(tol.get("percent", {}).get("value", 0.0)) / 100.0
    else:
        pct_tol = 0.0

    # 逐项判断
    abs_ok = (abs(float(a) - float(b)) <= abs_tol) if mode in ("absolute", "both") else True
    pct_base = max(abs(float(b)), 1e-9)  # 避免除零
    pct_ok = ((abs(float(a) - float(b)) / pct_base) <= pct_tol) if mode in ("percent", "both") else True

    return abs_ok and pct_ok
st.title("对账自动化 Demo（发票 × 账单）")
st.caption("上传两张表 → 匹配/差异/缺失/重复 → 一键导出异常清单")

# ---------- Helper: build sample data and download ----------
def build_sample_df(kind="invoices"):
    if kind == "invoices":
        df = pd.DataFrame({
            "vendor": ["V0001","V0001","V0002","V0003"],
            "invoice_no": ["INV001","INV002","INV010","INV021"],
            "amount": [10000, 5000, 8000, 12000],
            "currency": ["JPY","JPY","JPY","JPY"]
        })
    else:
        df = pd.DataFrame({
            "vendor": ["V0001","V0001","V0002","V0004"],
            "invoice_no": ["INV001","INV002","INV010","INV999"],
            "amount": [10000, 5200, 8000, 3000],
            "currency": ["JPY","JPY","JPY","JPY"]
        })
    return df

def df_to_excel_bytes(sheets: dict):
    """
    sheets: {"SheetName": pd.DataFrame, ...}
    return: bytes of an xlsx file
    """
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        for name, df in sheets.items():
            df.to_excel(writer, index=False, sheet_name=name[:31] or "Sheet1")
    return output.getvalue()

col_samp1, col_samp2, col_samp3 = st.columns(3)
with col_samp1:
    st.download_button(
        "下载示例发票表（invoices.xlsx）",
        data=df_to_excel_bytes({"invoices": build_sample_df("invoices")}),
        file_name="invoices_sample.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
with col_samp2:
    st.download_button(
        "下载示例账单表（bills.xlsx）",
        data=df_to_excel_bytes({"bills": build_sample_df("bills")}),
        file_name="bills_sample.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
with col_samp3:
    st.info("字段要求：vendor, invoice_no, amount, currency（大小写不敏感，列名可映射）", icon="ℹ️")

st.divider()

# ---------- Sidebar: settings ----------
with st.sidebar:
    st.header("对账参数")
    abs_thr = st.number_input("金额绝对差异阈值（同币种）", min_value=0.0, value=0.0, step=10.0)
    pct_thr = st.number_input("金额百分比阈值（0.05=5%）", min_value=0.0, value=0.0, step=0.01, format="%.2f")
    normalize_currency = st.checkbox("忽略币种大小写", value=True)
    group_duplicates = st.checkbox("合并重复行（vendor+invoice_no+currency 汇总）", value=True)
    show_raw = st.checkbox("显示原始数据", value=False)

# ---------- File uploaders ----------
c1, c2 = st.columns(2)
with c1:
    f_inv = st.file_uploader("上传发票表（invoices：.xlsx/.xls/.csv）", type=["xlsx","xls","csv"], key="inv")
with c2:
    f_bill = st.file_uploader("上传账单表（bills：.xlsx/.xls/.csv）", type=["xlsx","xls","csv"], key="bill")

# ---------- Parser ----------
def read_any(file):
    name = file.name.lower()
    if name.endswith(".csv"):
        return pd.read_csv(file)
    else:
        return pd.read_excel(file)

# ---------- Column mapping UI ----------
def guess_columns(df):
    cols_lower = {c.lower(): c for c in df.columns}
    def get(*cands):
        for c in cands:
            if c in cols_lower:
                return cols_lower[c]
        return None
    vendor = get("vendor","供应商","供应商编码","vendorcode","vendor_code")
    invno  = get("invoice_no","发票号","发票编号","invoice","invoice number")
    amt    = get("amount","金额","amt","total","price")
    curr   = get("currency","币种","curr","iso","ccy")
    return vendor, invno, amt, curr

def normalize_df(df, mapping):
    vendor, invno, amt, curr = mapping
    # 复制一份，避免修改原 DataFrame
    df = df.copy()
    # 转换基础列
    df[vendor] = df[vendor].astype(str).str.strip().str.upper()
    df[invno]  = df[invno].astype(str).str.strip().str.upper()
    df[curr]   = df[curr].astype(str).str.strip().str.upper()
    df[amt]    = pd.to_numeric(df[amt], errors="coerce").fillna(0.0)
    # 统一列名
    df = df.rename(columns={vendor:"vendor", invno:"invoice_no", amt:"amount", curr:"currency"})
    return df[["vendor","invoice_no","amount","currency"]]

def aggregate_duplicates(df):
    # 记录重复（用于报告）
    dup_mask = df.duplicated(subset=["vendor","invoice_no","currency"], keep=False)
    dups = df.loc[dup_mask].sort_values(["vendor","invoice_no","currency"])
    # 聚合
    agg = df.groupby(["vendor","invoice_no","currency"], as_index=False)["amount"].sum()
    return agg, dups

def reconcile(inv_df, bill_df, abs_thr=0.0, pct_thr=0.0):
    # 外连接对账
    merged = inv_df.merge(bill_df, on=["vendor","invoice_no","currency"], how="outer", suffixes=("_inv","_bill"))
    merged["amount_inv"] = merged["amount_inv"].fillna(0.0)
    merged["amount_bill"] = merged["amount_bill"].fillna(0.0)

    # 计算差异与阈值（绝对值 或 百分比，取更宽松的一方作为容忍）
    base = merged[["amount_inv","amount_bill"]].abs().max(axis=1)
    tol = np.maximum(abs_thr, base * pct_thr)
    merged["diff"] = merged["amount_inv"] - merged["amount_bill"]
    merged["within_tolerance"] = merged["diff"].abs() <= tol

    # 分类
    cond_missing_inv  = (merged["amount_inv"]  == 0.0) & (merged["amount_bill"] != 0.0)
    cond_missing_bill = (merged["amount_bill"] == 0.0) & (merged["amount_inv"]  != 0.0)
    cond_mismatch     = (~cond_missing_inv) & (~cond_missing_bill) & (~merged["within_tolerance"])

    matched  = merged[(~cond_missing_inv) & (~cond_missing_bill) & (merged["within_tolerance"])].copy()
    missing_in_invoices = merged[cond_missing_inv].copy()
    missing_in_bills    = merged[cond_missing_bill].copy()
    mismatches          = merged[cond_mismatch].copy()

    return merged, matched, mismatches, missing_in_invoices, missing_in_bills

# ---------- Main logic ----------
if f_inv is not None and f_bill is not None:
    inv_raw = read_any(f_inv)
    bill_raw = read_any(f_bill)

    # 显示原始数据
    if show_raw:
        st.subheader("原始数据预览")
        st.write("发票表（前100行）：")
        st.dataframe(inv_raw.head(100), use_container_width=True, height=240)
        st.write("账单表（前100行）：")
        st.dataframe(bill_raw.head(100), use_container_width=True, height=240)

    # 猜列名 + UI 映射
    inv_guess = guess_columns(inv_raw)
    bill_guess = guess_columns(bill_raw)
    st.subheader("列名映射")
    mcol1, mcol2 = st.columns(2)

    with mcol1:
        st.markdown("**发票表列映射**")
        inv_vendor = st.selectbox("vendor(发票)", inv_raw.columns, index=inv_raw.columns.get_loc(inv_guess[0]) if inv_guess[0] in inv_raw.columns else 0)
        inv_invno  = st.selectbox("invoice_no(发票)", inv_raw.columns, index=inv_raw.columns.get_loc(inv_guess[1]) if inv_guess[1] in inv_raw.columns else 0)
        inv_amt    = st.selectbox("amount(发票)", inv_raw.columns, index=inv_raw.columns.get_loc(inv_guess[2]) if inv_guess[2] in inv_raw.columns else 0)
        inv_curr   = st.selectbox("currency(发票)", inv_raw.columns, index=inv_raw.columns.get_loc(inv_guess[3]) if inv_guess[3] in inv_raw.columns else 0)

    with mcol2:
        st.markdown("**账单表列映射**")
        bill_vendor = st.selectbox("vendor(账单)", bill_raw.columns, index=bill_raw.columns.get_loc(bill_guess[0]) if bill_guess[0] in bill_raw.columns else 0)
        bill_invno  = st.selectbox("invoice_no(账单)", bill_raw.columns, index=bill_raw.columns.get_loc(bill_guess[1]) if bill_guess[1] in bill_raw.columns else 0)
        bill_amt    = st.selectbox("amount(账单)", bill_raw.columns, index=bill_raw.columns.get_loc(bill_guess[2]) if bill_guess[2] in bill_raw.columns else 0)
        bill_curr   = st.selectbox("currency(账单)", bill_raw.columns, index=bill_raw.columns.get_loc(bill_guess[3]) if bill_guess[3] in bill_raw.columns else 0)

    # 规范化
    inv_df = normalize_df(inv_raw, (inv_vendor, inv_invno, inv_amt, inv_curr))
    bill_df = normalize_df(bill_raw, (bill_vendor, bill_invno, bill_amt, bill_curr))

    if normalize_currency:
        inv_df["currency"]  = inv_df["currency"].str.upper()
        bill_df["currency"] = bill_df["currency"].str.upper()

    # 合并重复
    inv_dups = pd.DataFrame()
    bill_dups = pd.DataFrame()
    if group_duplicates:
        inv_df, inv_dups = aggregate_duplicates(inv_df)
        bill_df, bill_dups = aggregate_duplicates(bill_df)

    # 对账
    merged, matched, mismatches, missing_in_invoices, missing_in_bills = reconcile(inv_df, bill_df, abs_thr=abs_thr, pct_thr=pct_thr)

    # 指标卡
    st.subheader("结果概览")
    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("总条数", len(merged))
    k2.metric("匹配条数", len(matched))
    k3.metric("差异条数", len(mismatches))
    k4.metric("发票缺失", len(missing_in_invoices))
    k5.metric("账单缺失", len(missing_in_bills))

    # 展示表格
    st.markdown("### 差异明细（超出阈值）")
    st.dataframe(mismatches, use_container_width=True, height=260)

    st.markdown("### 发票缺失（账单有、发票无）")
    st.dataframe(missing_in_invoices, use_container_width=True, height=200)

    st.markdown("### 账单缺失（发票有、账单无）")
    st.dataframe(missing_in_bills, use_container_width=True, height=200)

    if group_duplicates:
        with st.expander("重复记录（入账或发票重复）"):
            st.write("发票重复（聚合前）")
            st.dataframe(inv_dups, use_container_width=True, height=180)
            st.write("账单重复（聚合前）")
            st.dataframe(bill_dups, use_container_width=True, height=180)

    # 导出
    st.subheader("下载结果")
    csv_bytes = mismatches.to_csv(index=False).encode("utf-8-sig")
    st.download_button("下载差异清单（CSV）", data=csv_bytes, file_name="mismatches.csv", mime="text/csv")

    # 多表 Excel 导出
    export_bytes = df_to_excel_bytes({
        "00_Merged": merged,
        "01_Matched": matched,
        "02_Mismatches": mismatches,
        "03_Missing_Invoices": missing_in_invoices,
        "04_Missing_Bills": missing_in_bills,
        "98_Dups_Invoices": inv_dups if not inv_dups.empty else pd.DataFrame(columns=inv_df.columns),
        "99_Dups_Bills": bill_dups if not bill_dups.empty else pd.DataFrame(columns=bill_df.columns)
    })
    st.download_button(
        "下载对账结果包（Excel，多Sheet）",
        data=export_bytes,
        file_name="reconciliation_results.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
else:
    st.info("请在上方上传发票表与账单表（可先下载示例文件体验）", icon="📄")
