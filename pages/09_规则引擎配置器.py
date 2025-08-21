# -*- coding: utf-8 -*-
"""
规则引擎配置器（第 9 页）
用途：通过可视化表单生成对账规则 rules.json，供“对账自动化 Demo”页面读取并应用。
仅依赖：streamlit、pandas（可选，仅用于表格编辑），标准库 json/datetime/io。
"""
import json
import io
from datetime import datetime
from typing import List, Dict, Any

import streamlit as st
import pandas as pd

st.set_page_config(page_title="规则引擎配置器（对账）", page_icon="🧩", layout="wide")
st.title("🧩 规则引擎配置器（对账）")
st.caption("定义【主键/字段映射/容差/日期/舍入/供应商别名/币种汇率/重复处理/模糊匹配】并导出为 rules.json。\
可导入既有 rules.json 进行编辑。")

# -------------------- 工具函数 --------------------
def _df_from_editor(df: pd.DataFrame | None, cols: List[str]) -> list[dict]:
    if df is None or df.empty:
        return []
    # 只保留指定列并丢弃空行
    df = df.reindex(columns=cols)
    df = df.dropna(how="all")
    # 去除两端空格
    for c in cols:
        if c in df.columns and df[c].dtype == "object":
            df[c] = df[c].astype(str).str.strip()
    return df.to_dict(orient="records")

def _rules_default() -> Dict[str, Any]:
    return {
        "schema_version": "1.0",
        "updated_at": datetime.utcnow().isoformat() + "Z",
        # 数据集命名（左表=发票，右表=台账/账单）
        "datasets": {"left_name": "invoices", "right_name": "ledger"},
        # 字段映射
        "column_mapping": {
            # 左/右表字段名（供代码读取）
            "left": {
                "vendor": "vendor",
                "invoice_no": "invoice_no",
                "amount": "amount",
                "currency": "currency",
                "date": "date"
            },
            "right": {
                "vendor": "vendor",
                "invoice_no": "invoice_no",
                "amount": "amount",
                "currency": "currency",
                "date": "date"
            }
        },
        # 主键（用于匹配）——按顺序组合
        "primary_key": ["vendor", "invoice_no", "currency"],
        # 容差规则
        "tolerance": {
            "mode": "both",   # absolute / percent / both
            "absolute": {"value": 10.0, "per_currency": {"JPY": 10.0, "CNY": 5.0}},
            "percent": {"value": 0.5}  # 0.5%（0.5 表示百分比）
        },
        # 日期与舍入
        "date_tolerance_days": 0,
        "rounding": {"amount_decimals": 2},
        # 重复处理策略
        "dedup": {"strategy": "sum"},  # keep_first / sum / error
        # 供应商别名映射
        "vendor_alias": [
            {"alias": "东京供应", "canonical": "Tokyo Supplies"},
            {"alias": "大坂服务", "canonical": "Osaka Service"}
        ],
        # 币种与汇率（可选）
        "currency": {
            "base": "CNY",
            "fx": {"JPY": 0.05, "USD": 7.2, "EUR": 7.9}  # 1 外币 = ? base
        },
        # 模糊匹配（对供应商名等）
        "fuzzy_match": {
            "enabled": False,
            "fields": ["vendor"],
            "threshold": 0.9  # 0~1
        },
        # 其它
        "options": {
            "allow_negative_amount": True,
            "strip_spaces": True
        }
    }

def _apply_rules_to_state(rules: Dict[str, Any]):
    st.session_state["rules"] = rules

def _ensure_rules():
    if "rules" not in st.session_state:
        st.session_state["rules"] = _rules_default()

_ensure_rules()

# -------------------- 顶部导入/导出 --------------------
with st.expander("📂 导入 / 导出", expanded=True):
    c1, c2, c3, c4 = st.columns([1.2,1,1,1.2])
    with c1:
        datasets_left = st.text_input("左表名称（展示用）", st.session_state["rules"]["datasets"]["left_name"])
    with c2:
        datasets_right = st.text_input("右表名称（展示用）", st.session_state["rules"]["datasets"]["right_name"])
    with c3:
        base_ccy = st.text_input("基础币种（base）", st.session_state["rules"]["currency"]["base"])
    with c4:
        st.caption("Tip: 名称仅用于可读性；代码按字段映射读取。")

    imp = st.file_uploader("导入现有 rules.json（可选）", type=["json"])
    imp_cols = st.columns([1, 1, 4])
    with imp_cols[0]:
        if st.button("加载到页面", use_container_width=True, disabled=(imp is None)):
            try:
                rules = json.load(imp)
                # 简单校验
                if "column_mapping" not in rules or "primary_key" not in rules:
                    st.error("JSON 缺少必要字段（column_mapping / primary_key）。")
                else:
                    _apply_rules_to_state(rules)
                    st.success("已加载到页面，下面可以继续编辑。")
            except Exception as e:
                st.error(f"解析失败：{e}")
    with imp_cols[1]:
        if st.button("恢复默认模板", use_container_width=True):
            _apply_rules_to_state(_rules_default())
            st.info("已恢复默认模板。")

# -------------------- 字段映射 & 主键 --------------------
st.subheader("1) 字段映射 & 主键")
st.caption("为左表（发票）与右表（台账）指定各字段名；主键决定匹配组合顺序。")

col_map = st.session_state["rules"]["column_mapping"]
pk = st.session_state["rules"]["primary_key"]

cm1, cm2 = st.columns(2)
with cm1:
    st.markdown("**左表（发票）字段**")
    l_vendor = st.text_input("vendor（左）", col_map["left"].get("vendor", "vendor"))
    l_invno  = st.text_input("invoice_no（左）", col_map["left"].get("invoice_no", "invoice_no"))
    l_amt    = st.text_input("amount（左）", col_map["left"].get("amount", "amount"))
    l_ccy    = st.text_input("currency（左）", col_map["left"].get("currency", "currency"))
    l_date   = st.text_input("date（左，可选）", col_map["left"].get("date", "date"))

with cm2:
    st.markdown("**右表（台账）字段**")
    r_vendor = st.text_input("vendor（右）", col_map["right"].get("vendor", "vendor"))
    r_invno  = st.text_input("invoice_no（右）", col_map["right"].get("invoice_no", "invoice_no"))
    r_amt    = st.text_input("amount（右）", col_map["right"].get("amount", "amount"))
    r_ccy    = st.text_input("currency（右）", col_map["right"].get("currency", "currency"))
    r_date   = st.text_input("date（右，可选）", col_map["right"].get("date", "date"))

pk_help = "按顺序组合。例如：vendor + invoice_no + currency"
pk_input = st.multiselect("主键（从以下集合中选择，顺序可拖动）",
                          options=["vendor", "invoice_no", "currency", "date"],
                          default=pk, help=pk_help)

# -------------------- 容差规则 --------------------
st.subheader("2) 容差规则（金额）")
t = st.session_state["rules"]["tolerance"]
row1 = st.columns([1,1,1])
with row1[0]:
    tol_mode = st.radio("模式", ["absolute", "percent", "both"], index=["absolute","percent","both"].index(t["mode"]), horizontal=True)
with row1[1]:
    abs_val = st.number_input("绝对容差（全局）", value=float(t["absolute"]["value"]), step=0.01)
with row1[2]:
    pct_val = st.number_input("百分比容差（%）", value=float(t["percent"]["value"]), step=0.1)

st.caption("为不同币种设置覆盖规则（可留空）。")
per_ccy_df = pd.DataFrame(
    [{"currency": k, "abs_tolerance": v} for k, v in (t["absolute"].get("per_currency") or {}).items()]
) if t["absolute"].get("per_currency") else pd.DataFrame(columns=["currency","abs_tolerance"])
per_ccy_df = st.data_editor(per_ccy_df, num_rows="dynamic", use_container_width=True,
                            column_config={"currency": st.column_config.TextColumn("币种", help="如 JPY/CNY/USD/EUR")},
                            key="abs_per_ccy")

# -------------------- 日期 & 舍入 --------------------
st.subheader("3) 日期/舍入")
row2 = st.columns([1,1,1,1])
with row2[0]:
    date_tol = st.number_input("日期容差（天）", value=int(st.session_state["rules"].get("date_tolerance_days", 0)), step=1, min_value=0)
with row2[1]:
    decs = st.number_input("金额小数位（舍入）", value=int(st.session_state["rules"]["rounding"]["amount_decimals"]), step=1, min_value=0, max_value=6)
with row2[2]:
    allow_neg = st.checkbox("允许负数（退款等）", value=bool(st.session_state["rules"]["options"].get("allow_negative_amount", True)))
with row2[3]:
    strip_spaces = st.checkbox("去除空格再匹配", value=bool(st.session_state["rules"]["options"].get("strip_spaces", True)))

# -------------------- 供应商别名 --------------------
st.subheader("4) 供应商别名映射")
alias_df_default = pd.DataFrame(st.session_state["rules"].get("vendor_alias", []))
alias_df_default = alias_df_default if not alias_df_default.empty else pd.DataFrame(columns=["alias","canonical"])
alias_df = st.data_editor(alias_df_default, num_rows="dynamic", use_container_width=True,
                          column_config={
                              "alias": st.column_config.TextColumn("别名（来账名称）"),
                              "canonical": st.column_config.TextColumn("规范名（系统/主数据）"),
                          })

# -------------------- 币种 & 汇率 --------------------
st.subheader("5) 币种与汇率（可选）")
c1, c2 = st.columns([1,3])
with c1:
    base = st.text_input("基础币种（base）", value=st.session_state["rules"]["currency"].get("base","CNY"))
with c2:
    fx_dict = st.session_state["rules"]["currency"].get("fx", {})
    fx_df = pd.DataFrame([{"currency": k, "to_base": v} for k, v in fx_dict.items()]) if fx_dict else pd.DataFrame(columns=["currency","to_base"])
    fx_df = st.data_editor(fx_df, num_rows="dynamic", use_container_width=True,
                           column_config={
                               "currency": st.column_config.TextColumn("币种"),
                               "to_base": st.column_config.NumberColumn("1 外币 = ? 基础币", step=0.0001),
                           })

# -------------------- 重复处理 & 模糊匹配 --------------------
st.subheader("6) 重复处理 & 模糊匹配")
c3, c4, c5 = st.columns([1,1,2])
with c3:
    strategy = st.selectbox("重复处理策略", ["keep_first","sum","error"],
                            index=["keep_first","sum","error"].index(st.session_state["rules"]["dedup"]["strategy"]))
with c4:
    fuzzy_on = st.checkbox("启用模糊匹配（供应商名等）", value=bool(st.session_state["rules"]["fuzzy_match"]["enabled"]))
with c5:
    threshold = st.slider("模糊阈值（0~1）", 0.0, 1.0, float(st.session_state["rules"]["fuzzy_match"]["threshold"]), 0.01)

# -------------------- 汇总 / 生成 JSON --------------------
st.subheader("7) 生成 rules.json")
# 将编辑器的内容汇总为规则对象
rules_obj = {
    "schema_version": st.session_state["rules"].get("schema_version","1.0"),
    "updated_at": datetime.utcnow().isoformat() + "Z",
    "datasets": {"left_name": datasets_left, "right_name": datasets_right},
    "column_mapping": {
        "left":  {"vendor": l_vendor, "invoice_no": l_invno, "amount": l_amt, "currency": l_ccy, "date": l_date},
        "right": {"vendor": r_vendor, "invoice_no": r_invno, "amount": r_amt, "currency": r_ccy, "date": r_date},
    },
    "primary_key": pk_input or ["vendor","invoice_no","currency"],
    "tolerance": {
        "mode": tol_mode,
        "absolute": {
            "value": float(abs_val),
            "per_currency": {str(row["currency"]).upper(): float(row["abs_tolerance"])
                             for row in _df_from_editor(st.session_state.get("abs_per_ccy"), ["currency","abs_tolerance"])
                             if str(row.get("currency","")).strip() != ""}
        },
        "percent": {"value": float(pct_val)}
    },
    "date_tolerance_days": int(date_tol),
    "rounding": {"amount_decimals": int(decs)},
    "dedup": {"strategy": strategy},
    "vendor_alias": _df_from_editor(alias_df, ["alias","canonical"]),
    "currency": {
        "base": base.upper().strip() if base else "",
        "fx": {str(r["currency"]).upper(): float(r["to_base"])
               for r in _df_from_editor(fx_df, ["currency","to_base"]) if str(r.get("currency","")).strip() != ""}
    },
    "fuzzy_match": {"enabled": bool(fuzzy_on), "fields": ["vendor"], "threshold": float(threshold)},
    "options": {"allow_negative_amount": bool(allow_neg), "strip_spaces": bool(strip_spaces)}
}

# 简要校验
problems = []
for side in ("left","right"):
    for req in ("vendor","invoice_no","amount","currency"):
        if not rules_obj["column_mapping"][side].get(req):
            problems.append(f"{'左' if side=='left' else '右'}表字段缺失：{req}")

if problems:
    st.error("校验失败：\n- " + "\n- ".join(problems))
else:
    st.success("规则校验通过 ✅")

# 预览 JSON
st.markdown("**预览（可复制）**")
st.code(json.dumps(rules_obj, ensure_ascii=False, indent=2), language="json")

# 下载 JSON
json_bytes = json.dumps(rules_obj, ensure_ascii=False, indent=2).encode("utf-8-sig")
st.download_button("💾 下载 rules.json", data=json_bytes, file_name="rules.json", mime="application/json")

# 存入会话（供本页再次打开时回填）
if st.button("保存为本页临时草稿（会话）"):
    _apply_rules_to_state(rules_obj)
    st.toast("已保存到会话（刷新/切页仍可回填）", icon="💡")

st.info("提示：下载的 rules.json 可放在仓库根目录或上传到“对账自动化 Demo”页面，由代码读取。")
