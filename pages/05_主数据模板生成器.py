# -*- coding: utf-8 -*-
import io
import pandas as pd
import streamlit as st

st.set_page_config(page_title="主数据模板生成器", page_icon="📘", layout="centered")
st.title("主数据模板生成器")
st.caption("一键生成供应商/成本中心/物料模板（含下拉校验、示例行）。下载为 Excel 发给业务同事填报。")

sheet_types = st.multiselect("选择要生成的模板 Sheet", ["供应商（vendors）","成本中心（cost_centers）","物料（items）"],
                             default=["供应商（vendors）","成本中心（cost_centers）"])

def build_excel(selected: list) -> bytes:
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="xlsxwriter") as w:
        wb = w.book
        # 维表/下拉项
        dv_sheet = wb.add_worksheet("ref")
        regions = ["CN","JP","US","EU"]
        currency = ["CNY","JPY","USD","EUR"]
        pay_terms = ["30","45","60","90"]
        dv_sheet.write_column(0,0, regions)
        dv_sheet.write_column(0,1, currency)
        dv_sheet.write_column(0,2, pay_terms)

        if "供应商（vendors）" in selected:
            df = pd.DataFrame([{
                "vendor_code":"V0001", "vendor_name":"示例供应商",
                "region":"JP", "currency":"JPY", "payment_term":"30",
                "bank_account":"XXXX-XXXX-XXXX", "swift":"ABCDEF12"
            }])
            df.to_excel(w, index=False, sheet_name="vendors")
            ws = w.sheets["vendors"]
            # 下拉校验
            ws.data_validation(1,2, 1000,2, {"validate":"list","source":"=ref!$A$1:$A$100"})
            ws.data_validation(1,3, 1000,3, {"validate":"list","source":"=ref!$B$1:$B$100"})
            ws.data_validation(1,4, 1000,4, {"validate":"list","source":"=ref!$C$1:$C$100"})

        if "成本中心（cost_centers）" in selected:
            df = pd.DataFrame([{
                "cc_code":"CC1001","cc_name":"销售部","dept":"Sales","owner":"张三","status":"Active"
            }])
            df.to_excel(w, index=False, sheet_name="cost_centers")

        if "物料（items）" in selected:
            df = pd.DataFrame([{
                "item_code":"ITM-001","item_name":"办公用品","uom":"PCS","category":"Office","status":"Active"
            }])
            df.to_excel(w, index=False, sheet_name="items")
    return buf.getvalue()

if st.button("生成并下载 Excel 模板", type="primary"):
    data = build_excel(sheet_types)
    st.download_button("下载主数据模板.xlsx", data=data,
        file_name="master_data_templates.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
