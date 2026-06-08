"""
Streamlit dashboard for AI Chatbot SaaS.
Run: streamlit run dashboard/app.py
"""

import os
import json
import streamlit as st
import requests
import pandas as pd

API_URL = os.getenv("API_URL", "http://localhost:8000")

st.set_page_config(page_title="AI Chatbot SaaS", page_icon="🤖", layout="wide")


# ── Auth helpers ──────────────────────────────────────────────────────────────

def api(method: str, path: str, **kwargs):
    token = st.session_state.get("token")
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    resp = requests.request(method, f"{API_URL}{path}", headers=headers, timeout=10, **kwargs)
    if resp.status_code == 401:
        st.session_state.clear()
        st.rerun()
    return resp


def login_page():
    st.title("🤖 AI Chatbot SaaS")
    tab1, tab2 = st.tabs(["Login", "Register"])

    with tab1:
        with st.form("login"):
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            if st.form_submit_button("Login"):
                r = requests.post(f"{API_URL}/auth/login", json={"email": email, "password": password})
                if r.status_code == 200:
                    data = r.json()
                    st.session_state["token"] = data["token"]
                    st.session_state["name"] = data.get("name", "")
                    st.rerun()
                else:
                    st.error(r.json().get("detail", "Login failed"))

    with tab2:
        with st.form("register"):
            name = st.text_input("Your Name")
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            if st.form_submit_button("Create Free Account (14-day trial)"):
                r = requests.post(f"{API_URL}/auth/register", json={"name": name, "email": email, "password": password})
                if r.status_code == 200:
                    st.session_state["token"] = r.json()["token"]
                    st.rerun()
                else:
                    st.error(r.json().get("detail", "Registration failed"))


# ── Pages ─────────────────────────────────────────────────────────────────────

def page_chatbots():
    st.header("My Chatbots")
    bots = api("GET", "/chatbots/").json()

    col1, col2 = st.columns([3, 1])
    with col2:
        if st.button("+ New Chatbot", type="primary"):
            st.session_state["new_bot"] = True

    if st.session_state.get("new_bot"):
        with st.form("new_bot_form"):
            st.subheader("Create Chatbot")
            bname = st.text_input("Business Name")
            btype = st.selectbox("Business Type", ["Dentist", "Gym", "Hair Salon", "Restaurant", "Law Firm", "Real Estate", "E-commerce", "Other"])
            color = st.color_picker("Widget Color", "#4F46E5")
            welcome = st.text_input("Welcome Message", "Hi! How can I help you today?")
            prompt = st.text_area("Custom System Prompt (optional)")
            if st.form_submit_button("Create"):
                r = api("POST", "/chatbots/", json={
                    "business_name": bname, "business_type": btype,
                    "widget_color": color, "welcome_message": welcome,
                    "system_prompt": prompt or None,
                })
                if r.status_code == 200:
                    st.success("Chatbot created!")
                    st.session_state.pop("new_bot", None)
                    st.rerun()
                else:
                    st.error(r.text)

    if not bots:
        st.info("No chatbots yet. Create your first one above.")
        return

    for bot in bots:
        with st.expander(f"🤖 {bot['business_name']} — {'🟢 Active' if bot['is_active'] else '🔴 Paused'}"):
            stats = api("GET", f"/chatbots/{bot['id']}/stats").json()
            c1, c2, c3 = st.columns(3)
            c1.metric("Total Messages", stats.get("total_messages", 0))
            c2.metric("Today", stats.get("messages_today", 0))
            c3.metric("Unique Sessions", stats.get("unique_sessions", 0))

            st.markdown("**Embed code — paste into your website:**")
            embed = f"""<script>
  window.AIChatbotId = {bot['id']};
  window.AIChatbotApiUrl = "{API_URL}";
</script>
<script src="{API_URL}/static/widget.js"></script>"""
            st.code(embed, language="html")

            col_a, col_b = st.columns(2)
            with col_a:
                active = st.toggle("Active", value=bool(bot["is_active"]), key=f"toggle_{bot['id']}")
                if active != bool(bot["is_active"]):
                    api("PUT", f"/chatbots/{bot['id']}", json={"is_active": active})
                    st.rerun()
            with col_b:
                if st.button("Delete", key=f"del_{bot['id']}"):
                    api("DELETE", f"/chatbots/{bot['id']}")
                    st.rerun()


def page_leads():
    st.header("Lead Manager")

    col1, col2, col3 = st.columns(3)
    status_filter = col1.selectbox("Status", ["all", "new", "contacted", "replied", "converted", "lost"])
    city_filter = col2.text_input("City filter")
    btype_filter = col3.text_input("Business type filter")

    params = {}
    if status_filter != "all":
        params["status"] = status_filter
    if city_filter:
        params["city"] = city_filter
    if btype_filter:
        params["business_type"] = btype_filter

    leads = api("GET", "/leads/", params=params).json()
    summary = api("GET", "/leads/stats/summary").json()

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total Leads", summary.get("total", 0))
    m2.metric("New", summary.get("by_status", {}).get("new", 0))
    m3.metric("Contacted", summary.get("by_status", {}).get("contacted", 0))
    m4.metric("Converted", summary.get("by_status", {}).get("converted", 0))

    if leads:
        df = pd.DataFrame(leads)
        cols = [c for c in ["business_name", "business_type", "city", "email", "phone", "status", "source"] if c in df.columns]
        st.dataframe(df[cols], use_container_width=True)

        st.markdown("---")
        st.subheader("Update Lead Status")
        lead_id = st.number_input("Lead ID", min_value=1, step=1)
        new_status = st.selectbox("New Status", ["new", "contacted", "replied", "converted", "lost"])
        notes = st.text_area("Notes")
        if st.button("Update"):
            api("PUT", f"/leads/{lead_id}", json={"status": new_status, "notes": notes})
            st.success("Updated")
            st.rerun()
    else:
        st.info("No leads found. Use the scraper to import leads.")

    with st.expander("Import leads from JSON file"):
        uploaded = st.file_uploader("Upload leads JSON", type="json")
        if uploaded and st.button("Import"):
            data = json.load(uploaded)
            r = api("POST", "/leads/bulk", json=data)
            st.success(r.json().get("message", "Imported"))
            st.rerun()


def page_outreach():
    st.header("Outreach Campaigns")

    campaigns = api("GET", "/outreach/campaigns").json()

    with st.expander("+ New Campaign"):
        with st.form("new_campaign"):
            name = st.text_input("Campaign Name")
            subject = st.text_input("Email Subject")
            body = st.text_area("Email Body", height=200,
                value="Hi {contact_name},\n\nI noticed {business_name} doesn't have a live chat...\n\nBest,\n{sender_name}")
            if st.form_submit_button("Create Campaign"):
                r = api("POST", "/outreach/campaigns", json={"name": name, "subject": subject, "body": body})
                st.success("Campaign created!")
                st.rerun()

    for c in campaigns:
        with st.expander(f"📧 {c['name']} — Sent: {c['sent_count']}"):
            st.text(f"Subject: {c['subject']}")
            st.text_area("Body", c["body"], height=150, disabled=True, key=f"body_{c['id']}")
            logs = api("GET", f"/outreach/campaigns/{c['id']}/logs").json()
            if logs:
                st.dataframe(pd.DataFrame(logs)[["business_name", "email", "status", "sent_at"]], use_container_width=True)


def page_scraper():
    st.header("Lead Scraper")
    st.info("Run scrapers from the command line and import the JSON here, or use the API keys below to search directly.")

    st.subheader("Google Maps Search")
    col1, col2, col3 = st.columns(3)
    btype = col1.text_input("Business type", "dentist")
    city = col2.text_input("City", "New York")
    count = col3.number_input("Max results", 5, 50, 20)

    if st.button("Search Google Maps"):
        with st.spinner("Searching..."):
            try:
                import sys
                sys.path.insert(0, str(__file__).replace("dashboard/app.py", "scraper"))
                from google_maps import search_businesses, enrich_leads
                leads = search_businesses(btype, city, max_results=count)
                leads = enrich_leads(leads)
                st.success(f"Found {len(leads)} businesses")
                st.dataframe(pd.DataFrame(leads), use_container_width=True)
                if st.button("Import these leads"):
                    r = api("POST", "/leads/bulk", json=leads)
                    st.success(r.json().get("message"))
            except Exception as e:
                st.error(f"Error: {e}. Make sure GOOGLE_MAPS_API_KEY is set in .env")


# ── Main ──────────────────────────────────────────────────────────────────────

if not st.session_state.get("token"):
    login_page()
else:
    with st.sidebar:
        st.title("🤖 AI Chatbot SaaS")
        st.write(f"Welcome, **{st.session_state.get('name', '')}**")
        page = st.radio("Navigation", ["Chatbots", "Leads", "Outreach", "Scraper"])
        if st.button("Logout"):
            st.session_state.clear()
            st.rerun()

    if page == "Chatbots":
        page_chatbots()
    elif page == "Leads":
        page_leads()
    elif page == "Outreach":
        page_outreach()
    elif page == "Scraper":
        page_scraper()
