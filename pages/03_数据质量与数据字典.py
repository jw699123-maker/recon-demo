# -*- coding: utf-8 -*-
import io, re
import pandas as pd
import numpy as np
import streamlit as st

st.set_page_config(page_title="数据质量与数据字典", page_icon="🧪", layout="wide")
st.title("数据质量与数据字典")
st.caption("上传 CSV/XLSX 自动生成字段画像、质量问题明细与可下载的数据字典（Excel 多 Sheet）")

def read_any(file):
    name = file.name.lower()
    if name.endswith(".csv"):
        return pd.read_csv(file)
    return pd.read_excel(file)

def profile(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for col in df.columns:
        s = df[col]
        dtype = str(s.dtype)
        non_null = int(s.notna().sum())
        nulls = int(s.isna().sum())
        null_pct = round(nulls * 100.0 / max(len(s),1), 2)
        uniq = int(s.nunique(dropna=True))
        sample = ", ".join(map(lambda x: str(x)[:20], s.dropna().astype(str).head(3)))
        # 数值/日期的 min/max
        mn = mx = ""
        if np.issubdtype(s.dropna().dtype, np.number):
            mn, mx = s.min(), s.max()
        elif np.issubdtype(s.dropna().dtype, "datetime64[ns]"):
            mn, mx = s.min(), s.max()
        rows.append([col, dtype, non_null, nulls, null_pct, uniq, mn, mx, sample])
    return pd.DataFrame(rows, columns=["column","dtype","non_null","nulls","null_pct%","unique","min","max","sample"])

def find_dupes(df: pd.DataFrame, keys: list) -> pd.DataFrame:
    if not keys: return pd.DataFrame()
    g = df.groupby(keys, dropna=False).size().reset_index(name="count")
    dkeys = g[g["count"]>1][keys]
    if dkeys.empty: return pd.DataFrame()
    mask = df.set_index(keys).index.isin(dkeys.set_index(keys).index)
    return df[mask].copy()

def to_excel_bytes(sheets: dict) -> bytes:
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="xlsxwriter") as w:
        for name, d in sheets.items():
            d = d if isinstance(d, pd.DataFrame) else pd.DataFrame(d)
            d.to_excel(w, index=False, sheet_name=name[:31] or "Sheet1")
    return buf.getvalue()

left, right = st.columns([1.2, 1])
with left:
    file = st.file_uploader("上传数据文件（CSV/XLSX）", type=["csv","xlsx","xls"])
    keys = st.multiselect("主键/唯一性检查字段（可多选）", [])
    if file:
        df = read_any(file)
        st.success(f"读取成功：{df.shape[0]} 行 × {df.shape[1]} 列")
        st.dataframe(df.head(10), use_container_width=True)
        # 根据文件列名更新 keys 选项
        keys = st.multiselect("主键/唯一性检查字段（可多选）", options=df.columns.tolist(), default=[df.columns[0]])
        prof = profile(df)
        dupes = find_dupes(df, keys)
        null_detail = df.loc[:, df.columns[df.isna().any()]].copy()
        # 规则示例：发票号与供应商编码的格式检查（可按需扩展）
        rule_issues = []
        if "invoice_no" in df.columns:
            bad = ~df["invoice_no"].astype(str).str.match(r"^[A-Za-z0-9\-\_/]{3,}$", na=False)
            if bad.any(): rule_issues.append(df.loc[bad, ["invoice_no"]].assign(rule="invoice_no 格式非法"))
        if "vendor_code" in df.columns:
            bad = ~df["vendor_code"].astype(str).str.match(r"^[A-Za-z0-9]{3,}$", na=False)
            if bad.any(): rule_issues.append(df.loc[bad, ["vendor_code"]].assign(rule="vendor_code 格式非法"))
        rule_df = pd.concat(rule_issues, ignore_index=True) if rule_issues else pd.DataFrame()

        with right:
            st.markdown("### 字段画像（数据字典）")
            st.dataframe(prof, use_container_width=True, height=320)

            st.markdown("### 质量问题摘要")
            c1, c2, c3 = st.columns(3)
            c1.metric("空值列数", int((prof["nulls"]>0).sum()))
            c2.metric("重复主键行", 0 if dupes.empty else dupes.shape[0])
            c3.metric("规则异常数", 0 if rule_df.empty else rule_df.shape[0])

            st.markdown("#### 下载完整报告")
            report = to_excel_bytes({
                "data_dictionary": prof,
                "duplicates": dupes if not dupes.empty else pd.DataFrame({"msg":["无重复"]}),
                "null_columns": null_detail if not null_detail.empty else pd.DataFrame({"msg":["无空值"]}),
                "rule_issues": rule_df if not rule_df.empty else pd.DataFrame({"msg":["无规则异常"]}),
                "sample_data": df.head(200)
            })
            st.download_button(
                "下载 Excel 报告（多 Sheet）",
                data=report,
                file_name="data_quality_report.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
    else:
        st.info("请在左侧上传数据，或先到『对账自动化 Demo』导出差异表再回这里分析。")
