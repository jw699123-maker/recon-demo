# -*- coding: utf-8 -*-
import streamlit as st
from datetime import date

st.set_page_config(page_title="日文邮件模板集（业务沟通）", page_icon="📧", layout="centered")
st.title("日文邮件模板集（业务沟通）")

scene = st.selectbox("場面 / Scene", [
    "支払期日ご案内（柔らかめ）",
    "金額差異のご確認",
    "請求書の再送依頼",
    "資料・証憑のご提出依頼",
    "入金確認のお願い",
    "お問い合わせ（一般）",
])

col1, col2 = st.columns(2)
with col1:
    vendor = st.text_input("会社名", "Tokyo Supplies")
    person = st.text_input("ご担当者", "田中 様")
    inv    = st.text_input("請求書番号", "INV-2025-001")
    amt    = st.text_input("金額", "10,000")
    ccy    = st.text_input("通貨", "JPY")
with col2:
    overdue = st.number_input("超過日数", 0, 365, 7)
    myco  = st.text_input("自社名", "杭州××科技有限公司")
    myper = st.text_input("担当", "王俊")
    today = st.date_input("日付", value=date.today())

jp = {
"支払期日ご案内（柔らかめ）":
f"""{vendor} {person}
平素より大変お世話になっております。
請求書 {inv}（金額：{amt} {ccy}）につきまして、支払期日が近づいております／{overdue}日超過しております。
お手数ですが、お支払予定または不足資料の有無をご教示いただけますと幸いです。
何卒よろしくお願い申し上げます。
{myco}  {myper}
{today}""",

"金額差異のご確認":
f"""{vendor} {person}
いつもお世話になっております。
請求書 {inv} について、弊方記録との金額差異（{amt} {ccy}）が確認されました。
正しい金額または修正後の請求書／対帳表をご共有ください。
よろしくお願いいたします。
{myco}  {myper}
{today}""",

"請求書の再送依頼":
f"""{vendor} {person}
お世話になっております。
請求書 {inv} の再送をお願いできますでしょうか。PDF版でも問題ございません。
何卒よろしくお願いいたします。
{myco}  {myper}
{today}""",

"資料・証憑のご提出依頼":
f"""{vendor} {person}
お世話になっております。
請求書 {inv} に関する領収書・納品書・契約書等の証憑をご提出いただけますでしょうか。
入金処理のため、何卒ご協力をお願い申し上げます。
{myco}  {myper}
{today}""",

"入金確認のお願い":
f"""{vendor} {person}
いつもお世話になっております。
請求書 {inv}（{amt} {ccy}）の入金状況につきまして、確認のほどお願い申し上げます。
お手数ですが、ご対応のほどよろしくお願いいたします。
{myco}  {myper}
{today}""",

"お問い合わせ（一般）":
f"""{vendor} {person}
お世話になっております。
下記件名についてご教示ください：請求書 {inv} / 金額 {amt} {ccy}。
以上、よろしくお願いいたします。
{myco}  {myper}
{today}"""
}

body = jp[scene]
st.text_area("メール本文（日本語）", body, height=300)
st.download_button("TXT ダウンロード", body.encode("utf-8"), file_name="mail_jp.txt")
