# -*- coding: utf-8 -*-
import streamlit as st
from datetime import date

st.set_page_config(page_title="双语 SOP / 邮件模板生成器", page_icon="✉️", layout="centered")
st.title("双语 SOP / 邮件模板生成器")
st.caption("选择场景 → 填写关键信息 → 一键生成 中文/日文/双语 邮件正文，并可复制/下载")

scene = st.selectbox("场景", ["到期提醒（温和）","金额差异说明","发票/凭证缺失","资料补充请求"])
lang  = st.radio("语言", ["中文","日文","双语"], horizontal=True)

col1, col2 = st.columns(2)
with col1:
    vendor = st.text_input("供应商名称/会社名", "Tokyo Supplies")
    to_person = st.text_input("对方联系人", "田中 様")
    inv = st.text_input("发票号/請求書番号", "INV-2025-001")
    amt = st.text_input("金额", "10,000")
    ccy = st.text_input("币种", "JPY")
with col2:
    overdue = st.number_input("逾期天数（若适用）", 0, 365, 15)
    my_company = st.text_input("我方公司名", "杭州××科技有限公司")
    my_person  = st.text_input("我方联系人", "王俊")
    my_email   = st.text_input("我方邮箱", "ap@yourcompany.com")
    today = st.date_input("日期", value=date.today())

cn_templates = {
    "到期提醒（温和）": f"""尊敬的{vendor}（{to_person}）您好：
贵司发票 {inv}（金额：{amt} {ccy}）将于近期到期/已逾期 {overdue} 天。为不影响双方合作，请协助确认付款计划或告知需要我们补充的资料。感谢配合！
此致
{my_company}  {my_person}
{today}""",

    "金额差异说明": f"""尊敬的{vendor}（{to_person}）您好：
我们在核对发票 {inv} 时发现与系统记录存在差异（金额：{amt} {ccy}）。烦请协助核对并反馈正确金额或修订后的发票/对账单。感谢！
{my_company}  {my_person}
{today}""",

    "发票/凭证缺失": f"""尊敬的{vendor}（{to_person}）您好：
发票 {inv} 所需的发票影印件/收据/送货单尚未收到。为尽快完成入账与付款，请您补充相关凭证并回复本邮件。谢谢！
{my_company}  {my_person}
{today}""",

    "资料补充请求": f"""尊敬的{vendor}（{to_person}）您好：
为匹配贵司发票 {inv}（金额：{amt} {ccy}），我们需要如下信息：开票抬头、税号、银行账户/Swift、联系人电话等。收到后我们将立即推进。谢谢！
{my_company}  {my_person}
{today}"""
}

jp_templates = {
    "到期提醒（温和）": f"""{vendor} {to_person}
平素より大変お世話になっております。
請求書 {inv}（金額：{amt} {ccy}）につきまして、支払期日が近づいております／{overdue}日超過しております。お手数ですが、お支払予定または不足資料の有無をご教示いただけますと幸いです。
何卒よろしくお願い申し上げます。
{my_company}  {my_person}
{today}""",

    "金额差异说明": f"""{vendor} {to_person}
いつもお世話になっております。
請求書 {inv} について、弊方記録との金額差異（{amt} {ccy}）が確認されました。ご確認の上、正しい金額または修正後の請求書／対帳表をご共有ください。
よろしくお願いいたします。
{my_company}  {my_person}
{today}""",

    "发票/凭证缺失": f"""{vendor} {to_person}
お世話になっております。
請求書 {inv} に関する写し／領収書／納品書等のご提出が未着です。入金処理のため、必要資料をご送付いただけますでしょうか。
何卒よろしくお願いいたします。
{my_company}  {my_person}
{today}""",

    "资料补充请求": f"""{vendor} {to_person}
お世話になっております。
請求書 {inv}（金額：{amt} {ccy}）の照合にあたり、以下情報のご提供をお願い申し上げます：請求宛名、税番号、銀行口座（SWIFT）、ご担当連絡先等。
ご対応のほどよろしくお願いいたします。
{my_company}  {my_person}
{today}"""
}

def render():
    cn = cn_templates[scene]
    jp = jp_templates[scene]
    if lang == "中文":
        st.text_area("中文邮件正文", cn, height=220)
        st.download_button("下载为 TXT（中文）", cn.encode("utf-8"), file_name="mail_cn.txt")
    elif lang == "日文":
        st.text_area("日文メール本文", jp, height=220)
        st.download_button("TXT ダウンロード（日本語）", jp.encode("utf-8"), file_name="mail_jp.txt")
    else:
        both = "【中文】\n" + cn + "\n\n【日本語】\n" + jp
        st.text_area("双语正文", both, height=360)
        st.download_button("下载为 TXT（双语）", both.encode("utf-8"), file_name="mail_cn_jp.txt")

render()
