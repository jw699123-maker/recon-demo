# -*- coding: utf-8 -*-
import io
import pandas as pd
import streamlit as st

st.set_page_config(page_title="RPA 对账机器人 Demo（UiPath）", page_icon="🤖", layout="wide")
st.title("RPA 对账机器人 Demo（UiPath）")
st.caption("下载 UiPath 资产（Main.xaml + 示例 Excel），按步骤在本地 UiPath Studio 运行；本页提供讲解脚本与附件。")

# --- 示例 Excel 构造 ---
def demo_invoices():
    df = pd.DataFrame({
        "vendor":["V0001","V0001","V0003","V0005"],
        "invoice_no":["INV001","INV002","INV077","INV088"],
        "amount":[10000,5000,5600,1300],
        "currency":["JPY","JPY","JPY","CNY"]
    })
    return df

def demo_ledger():
    df = pd.DataFrame({
        "vendor":["V0001","V0001","V0003"],
        "invoice_no":["INV001","INV002","INV077"],
        "amount":[10000,4800,5600],
        "currency":["JPY","JPY","JPY"]
    })
    return df

def to_excel_bytes(sheets: dict):
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="xlsxwriter") as w:
        for name, df in sheets.items():
            df.to_excel(w, index=False, sheet_name=name[:31] or "Sheet1")
    return buf.getvalue()

# --- 极简 Main.xaml（UiPath） ---
Uipath_XAML = """<?xml version="1.0" encoding="utf-8"?>
<Activity x:Class="Main" xmlns="http://schemas.microsoft.com/netfx/2009/xaml/activities"
 xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml"
 xmlns:ui="http://schemas.uipath.com/workflow/activities"
 xmlns:m="clr-namespace:Microsoft.VisualBasic;assembly=System"
 DisplayName="Main">
 <Sequence DisplayName="AP Reconciliation">
  <ui:ExcelApplicationScope DisplayName="Open Invoices.xlsx" WorkbookPath="[in_InvoicePath]">
   <ui:ReadRange DisplayName="Read Invoices" SheetName="invoices" Range="A1" AddHeaders="True" DataTable="[dtInv]" />
  </ui:ExcelApplicationScope>
  <ui:ExcelApplicationScope DisplayName="Open Ledger.xlsx" WorkbookPath="[in_LedgerPath]">
   <ui:ReadRange DisplayName="Read Ledger" SheetName="ledger" Range="A1" AddHeaders="True" DataTable="[dtLed]" />
  </ui:ExcelApplicationScope>
  <!-- 计算差异：发票存在于发票表但不在台账 或 金额不相等 -->
  <Assign DisplayName="Build Diff">
    <Assign.To>
      <OutArgument x:TypeArguments="x:Object">[dtDiff]</OutArgument>
    </Assign.To>
    <Assign.Value>
      [ (From inv In dtInv.AsEnumerable()
         Group Join led In dtLed.AsEnumerable()
         On inv("invoice_no").ToString Equals led("invoice_no").ToString
         Into j=Group
         From l In j.DefaultIfEmpty()
         Where l Is Nothing OrElse CDec(inv("amount")) &lt;&gt; CDec(If(l Is Nothing, 0, l("amount")))
         Select inv).CopyToDataTable() ]
    </Assign.Value>
  </Assign>
  <ui:ExcelApplicationScope DisplayName="Write Diff" WorkbookPath="[out_DiffPath]">
    <ui:WriteRange DisplayName="Write Diff" DataTable="[dtDiff]" SheetName="diff" StartingCell="A1" AddHeaders="True" />
  </ui:ExcelApplicationScope>
 </Sequence>
</Activity>
"""

with st.sidebar:
    st.subheader("一键下载资产")
    st.download_button("下载示例 Invoices.xlsx",
        data=to_excel_bytes({"invoices": demo_invoices()}),
        file_name="Invoices.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    st.download_button("下载示例 Ledger.xlsx",
        data=to_excel_bytes({"ledger": demo_ledger()}),
        file_name="Ledger.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    st.download_button("下载 UiPath Main.xaml", data=Uipath_XAML.encode("utf-8"),
        file_name="Main.xaml", mime="application/xml")

st.markdown("### 本地运行步骤（UiPath Studio）")
st.markdown("""
1. 新建空白流程 **AP_Recon**，把下载的 **Main.xaml** 覆盖到项目根目录。
2. 在 **Variables** 面板新增：`in_InvoicePath`、`in_LedgerPath`、`out_DiffPath`（String）。
3. 在流程开始处给 3 个变量赋值（或使用 **Arguments** 配置）：  
   - `in_InvoicePath`: `Invoices.xlsx`  
   - `in_LedgerPath`: `Ledger.xlsx`  
   - `out_DiffPath`: `Diff.xlsx`
4. 运行后生成 `Diff.xlsx`，即为差异清单（缺失或金额不一致）。
5. 演示讲解要点：**批量可扩展 / 与 Orchestrator 结合 / 可换 OCR 模块做票据字段抽取**。
""")

st.markdown("### 面试讲解脚本（30 秒）")
st.info("“RPA 端负责**文件读写与自动比对**、异常导出；你现在看到的 Streamlit 端提供**对外展示与交互**。上线后，财务只需把两份表丢进机器人目录，系统 1 分钟给出差异表。”")
