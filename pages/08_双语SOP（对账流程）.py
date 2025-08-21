# -*- coding: utf-8 -*-
import io
import streamlit as st

st.set_page_config(page_title="双语 SOP（对账流程）", page_icon="📘", layout="wide")
st.title("双语 SOP（对账流程）")

lang = st.radio("语言 / Language", ["中文", "日本語", "双语"], horizontal=True)
scope = st.multiselect("流程范围（可选）", ["发票接收与校验","账单/台账准备","自动对账与复核","异常沟通与闭环","归档与交接"],
                       default=["发票接收与校验","自动对账与复核","异常沟通与闭环"])

def sop_cn():
    return f"""# 对账流程 SOP（中文）
## 1. 发票接收与校验
- 渠道：邮箱/供应商门户；命名规范：`供应商_发票号_日期.pdf`
- 检查：抬头/税号/币种/金额/发票影像清晰度
- 录入清单：`Invoices.xlsx`（vendor, invoice_no, amount, currency, date）

## 2. 账单/台账准备
- 从 ERP 导出应付台账 `Ledger.xlsx`，字段：vendor, invoice_no, amount, currency
- 字段对齐与主键：`vendor + invoice_no + currency`
- 容差设置：金额差异 ≤ 0.5% 或 ≤ 10 JPY

## 3. 自动对账与复核
- RPA/脚本读取两表 → 匹配、金額差异、缺失/多余
- 生成差异表 `Diff.xlsx`；复核人二签
- 高风险（90+ 逾期/大额差异）单独贴标签

## 4. 异常沟通与闭环
- 邮件模板：日文模板集（逾期提醒/差异说明/资料补充）
- 记录结论：责任方、原因、解决时限
- 二次对账确认；必要时出具对账单盖章

## 5. 归档与交接
- 归档清单：发票影像、对账结果、沟通记录、SOP 版本
- 目录规范：`FY/Month/Vendor/`
- 每月复盘改进点
"""

def sop_jp():
    return """# 照合手順書（日本語）

## 1. 請求書の受領と確認
- 受領経路：メール／ポータル、ファイル命名規則：`Vendor_InvoiceNo_Date.pdf`
- 確認項目：宛名・税番号・通貨・金額・画質
- 入力台帳：`Invoices.xlsx`（vendor, invoice_no, amount, currency, date）

## 2. 台帳準備
- ERP から AP 台帳 `Ledger.xlsx` を出力（vendor, invoice_no, amount, currency）
- 主キー：`vendor + invoice_no + currency`
- 許容差：0.5% または 10 JPY 以下

## 3. 自動照合とレビュー
- RPA/スクリプトで2表を照合 → 差異/不足/重複
- `Diff.xlsx` を出力、レビュアーが二重承認
- ハイリスク（90+ 超過や高額差異）はタグ付け

## 4. 例外対応とクローズ
- メールテンプレ：督促／差異説明／資料追加
- 記録：責任区分、原因、期限
- 再照合してクローズ、必要に応じて対帳票に捺印

## 5. 保管と引継ぎ
- 保管物：請求書PDF、結果、コミュニケーション、SOP 版
- フォルダ規約：`FY/Month/Vendor/`
- 月次ふりかえり
"""

cn = sop_cn()
jp = sop_jp()
md = cn if lang=="中文" else (jp if lang=="日本語" else (cn + "\n---\n" + jp))

st.markdown(md)
st.download_button("下载为 Markdown（.md）", data=md.encode("utf-8"),
                   file_name="SOP_AP_Reconciliation.md",
                   mime="text/markdown")
