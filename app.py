# app.py
import streamlit as st
import os
from datetime import datetime
from db import (
    init_db,
    add_item,
    get_items,
    get_item_by_id,
    update_item_status,
    add_claim,
    approve_claim,
    get_stats,
)
from matching import calculate_match_score


# ==================== PAGE CONFIG ====================
st.set_page_config(page_title="College Lost & Found", page_icon="🔍", layout="wide")
init_db()


# ==================== CUSTOM CSS (this is the "attractive UI" layer) ====================
def inject_css():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700&display=swap');

    html, body, [class*="css"]  { font-family: 'Poppins', sans-serif; }

    /* Gradient hero title */
    .hero-title {
        font-size: 2.3rem;
        font-weight: 700;
        background: linear-gradient(90deg, #7C5CFC 0%, #FF6EC7 50%, #FFB56B 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0;
    }
    .hero-sub { color: #A6A4C0; font-size: 1.05rem; margin-top: -6px; }

    /* Buttons */
    .stButton > button {
        border-radius: 999px;
        border: none;
        background: linear-gradient(90deg, #7C5CFC, #FF6EC7);
        color: white;
        font-weight: 600;
        padding: 0.55rem 1.4rem;
        transition: transform 0.15s ease, box-shadow 0.15s ease;
        box-shadow: 0 4px 14px rgba(124, 92, 252, 0.35);
    }
    .stButton > button:hover {
        transform: translateY(-2px) scale(1.02);
        box-shadow: 0 6px 20px rgba(124, 92, 252, 0.5);
    }

    /* Metric cards */
    .metric-card {
        border-radius: 16px;
        padding: 18px 20px;
        background: linear-gradient(135deg, rgba(124,92,252,0.15), rgba(255,110,199,0.10));
        border: 1px solid rgba(124,92,252,0.35);
        text-align: center;
    }
    .metric-value { font-size: 1.8rem; font-weight: 700; color: #F1F0FB; }
    .metric-label { font-size: 0.85rem; color: #A6A4C0; margin-top: 2px; }

    /* Item cards */
    .item-card {
        border-radius: 14px;
        padding: 16px 18px;
        margin-bottom: 14px;
        background: #171A24;
        border: 1px solid #2A2E3E;
        border-left: 5px solid var(--accent, #7C5CFC);
        transition: transform 0.15s ease, box-shadow 0.15s ease;
    }
    .item-card:hover {
        transform: translateY(-3px);
        box-shadow: 0 8px 22px rgba(0,0,0,0.35);
        border-color: #3D4258;
    }
    .item-title { font-weight: 600; font-size: 1.05rem; color: #F1F0FB; }
    .item-meta { color: #9694B3; font-size: 0.85rem; margin-top: 2px; }

    /* Badges */
    .badge {
        display: inline-block;
        padding: 3px 12px;
        border-radius: 999px;
        font-size: 0.75rem;
        font-weight: 600;
        margin-right: 6px;
    }
    .badge-lost   { background: rgba(255, 110, 110, 0.18); color: #FF8C8C; }
    .badge-found  { background: rgba(94, 227, 168, 0.18); color: #5EE3A8; }
    .badge-open   { background: rgba(255, 181, 107, 0.18); color: #FFB56B; }
    .badge-returned { background: rgba(124, 92, 252, 0.20); color: #B3A2FF; }
    .badge-cat    { background: rgba(255,255,255,0.08); color: #C9C7E0; }

    /* Sidebar */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #14151F, #0F1117);
        border-right: 1px solid #2A2E3E;
    }
    </style>
    """, unsafe_allow_html=True)


CATEGORY_ACCENT = {
    "lost": "#FF6E6E",
    "found": "#5EE3A8",
}


def type_badge(item_type):
    cls = "badge-lost" if item_type == "lost" else "badge-found"
    label = "LOST" if item_type == "lost" else "FOUND"
    return f'<span class="badge {cls}">{label}</span>'


def status_badge(status):
    cls = "badge-open" if status == "open" else "badge-returned"
    label = "Open" if status == "open" else "Returned"
    return f'<span class="badge {cls}">{label}</span>'


def render_item_card(item):
    accent = CATEGORY_ACCENT.get(item["type"], "#7C5CFC")
    badges = type_badge(item["type"]) + status_badge(item["status"]) + \
        f'<span class="badge badge-cat">{item["category"]}</span>'

    st.markdown(f"""
    <div class="item-card" style="--accent:{accent}">
        <div class="item-title">{item['description'][:70]}</div>
        <div style="margin:8px 0">{badges}</div>
        <div class="item-meta">📍 {item['location']} &nbsp;·&nbsp; 📅 {item['date_lost_found']}</div>
        <div class="item-meta">Reported by {item['name']} ({item['branch']})</div>
    </div>
    """, unsafe_allow_html=True)

    col_img, col_info = st.columns([1, 3])
    with col_img:
        if item.get("image_path") and os.path.exists(item["image_path"]):
            st.image(item["image_path"], width=140)

    with col_info:
        with st.expander("View contact details"):
            st.write(f"**Contact:** {item['contact']}")
            if item.get("email"):
                st.write(f"**Email:** {item['email']}")

        if item["type"] == "found" and item["status"] == "open":
            with st.expander("I think this is mine"):
                with st.form(key=f"claim_{item['id']}"):
                    c_name = st.text_input("Your name", key=f"cn_{item['id']}")
                    c_contact = st.text_input("Your contact", key=f"cc_{item['id']}")
                    c_msg = st.text_area(
                        "Describe it in your own words",
                        key=f"cm_{item['id']}",
                        placeholder="Include a detail only the real owner would know",
                    )
                    send = st.form_submit_button("Send claim")
                    if send:
                        if not (c_name and c_contact and c_msg):
                            st.error("Please fill in every field.")
                        else:
                            add_claim(item["id"], c_name, c_contact, c_msg)
                            st.success("Claim sent! The finder will be able to review it.")


def save_upload(uploaded_file, item_type):
    if uploaded_file:
        folder = f"uploads/{item_type}"
        os.makedirs(folder, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}_{uploaded_file.name}"
        filepath = os.path.join(folder, filename)
        with open(filepath, "wb") as f:
            f.write(uploaded_file.getvalue())
        return filepath
    return None


inject_css()

st.markdown('<div class="hero-title">🔍 College Lost &amp; Found</div>', unsafe_allow_html=True)
st.markdown('<div class="hero-sub">Report it. Match it. Get it back.</div>', unsafe_allow_html=True)
st.write("")

st.sidebar.markdown("### 🔍 Navigate")
page = st.sidebar.radio(
    "",
    ["📊 Dashboard", "📍 Report Found Item", "📢 Report Lost Item", "📋 Browse Items"],
    label_visibility="collapsed",
)

CATEGORIES = ["Electronics", "Books", "Clothing", "Accessories", "Stationery", "Other"]
BRANCHES = ["CSE", "IT", "ECE", "EEE", "Mechanical", "Civil", "Business", "MBA", "BBA"]


# ==================== DASHBOARD ====================
if page == "📊 Dashboard":
    stats = get_stats()

    c1, c2, c3, c4 = st.columns(4)
    metric_data = [
        (c1, stats["total_lost"], "Lost items"),
        (c2, stats["total_found"], "Found items"),
        (c3, stats["total_returned"], "Returned"),
        (c4, f"{stats['return_rate']}%", "Return rate"),
    ]
    for col, value, label in metric_data:
        with col:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-value">{value}</div>
                <div class="metric-label">{label}</div>
            </div>
            """, unsafe_allow_html=True)

    st.write("")
    if stats["pending_claims"]:
        st.info(f"⏳ {stats['pending_claims']} pending claim(s) awaiting review")

    st.write("")
    st.subheader("📈 How it works")
    st.markdown("""
    1. **Found something?** Report it with a photo and details
    2. **Lost something?** Report it — we auto-match against found items
    3. **Claim an item** by describing something only the real owner would know
    4. **Track progress** on this dashboard as items get returned
    """)


# ==================== REPORT FOUND ITEM ====================
elif page == "📍 Report Found Item":
    st.subheader("📍 Report a found item")

    with st.form("found_form", clear_on_submit=True):
        col1, col2 = st.columns(2)

        with col1:
            category = st.selectbox("Category", CATEGORIES)
            custom_item = None
            if category == "Other":
                custom_item = st.text_input("Item name", placeholder="Write your item name...")
            location = st.text_input("Where did you find it?", placeholder="e.g. Library, Canteen")
            date_found = st.date_input("Date found", value=datetime.now())

        with col2:
            name = st.text_input("Your name *")
            branch = st.selectbox("Branch *", BRANCHES)
            section = st.text_input("Section (optional)")
            contact = st.text_input("Contact number *")
            email = st.text_input("Email (optional)")

        description = st.text_area(
            "Description *",
            placeholder="Brand, color, model, size, any unique marks...",
        )
        image = st.file_uploader("Upload photo (recommended)", type=["jpg", "jpeg", "png"])
        submitted = st.form_submit_button("Submit found report")

        if submitted:
            if not all([category, location, name, branch, contact, description]):
                st.error("Please fill all required fields (marked with *)")
            elif category == "Other" and not custom_item:
                st.error("Please specify the item name for 'Other' category")
            else:
                final_category = f"Other: {custom_item}" if custom_item else category
                image_path = save_upload(image, "found")

                item_id = add_item(
                    item_type="found", category=final_category, description=description,
                    location=location, date_lost_found=date_found.isoformat(),
                    name=name, branch=branch, section=section,
                    contact=contact, email=email, image_path=image_path,
                )
                st.success(f"✅ Found item reported! (ID: {item_id})")

                lost_items = get_items(item_type="lost", status="open")
                matches = [
                    (li, calculate_match_score(li, {
                        "category": final_category, "description": description, "location": location,
                    }))
                    for li in lost_items
                ]
                matches = [(li, s) for li, s in matches if s >= 70]
                matches.sort(key=lambda pair: pair[1], reverse=True)

                if matches:
                    st.markdown("#### 🎯 Possible matches")
                    for li, score in matches[:3]:
                        with st.expander(f"{score}% match — {li['description'][:50]}..."):
                            st.write(f"**Location:** {li['location']}")
                            st.write(f"**Reported by:** {li['name']} ({li['branch']})")
                            st.write(f"**Contact:** {li['contact']}")


# ==================== REPORT LOST ITEM ====================
elif page == "📢 Report Lost Item":
    st.subheader("📢 Report a lost item")

    with st.form("lost_form", clear_on_submit=True):
        col1, col2 = st.columns(2)

        with col1:
            category = st.selectbox("Category", CATEGORIES)
            custom_item = None
            if category == "Other":
                custom_item = st.text_input("Item name", placeholder="Write your item name...")
            location = st.text_input("Where did you lose it?", placeholder="e.g. Library, Canteen")
            date_lost = st.date_input("Date lost", value=datetime.now())

        with col2:
            name = st.text_input("Your name *")
            branch = st.selectbox("Branch *", BRANCHES)
            section = st.text_input("Section (optional)")
            contact = st.text_input("Contact number *")
            email = st.text_input("Email (optional)")

        description = st.text_area(
            "Description *",
            placeholder="Brand, color, model, size, any unique marks...",
        )
        image = st.file_uploader("Upload photo (optional)", type=["jpg", "jpeg", "png"])
        submitted = st.form_submit_button("Submit lost report")

        if submitted:
            if not all([category, location, name, branch, contact, description]):
                st.error("Please fill all required fields (marked with *)")
            elif category == "Other" and not custom_item:
                st.error("Please specify the item name for 'Other' category")
            else:
                final_category = f"Other: {custom_item}" if custom_item else category
                image_path = save_upload(image, "lost")

                item_id = add_item(
                    item_type="lost", category=final_category, description=description,
                    location=location, date_lost_found=date_lost.isoformat(),
                    name=name, branch=branch, section=section,
                    contact=contact, email=email, image_path=image_path,
                )
                st.success(f"✅ Lost item reported! (ID: {item_id})")

                found_items = get_items(item_type="found", status="open")
                matches = [
                    (fi, calculate_match_score({
                        "category": final_category, "description": description, "location": location,
                    }, fi))
                    for fi in found_items
                ]
                matches = [(fi, s) for fi, s in matches if s >= 70]
                matches.sort(key=lambda pair: pair[1], reverse=True)

                if matches:
                    st.markdown("#### 🎯 Possible matches")
                    for fi, score in matches[:3]:
                        with st.expander(f"{score}% match — {fi['description'][:50]}..."):
                            st.write(f"**Location:** {fi['location']}")
                            st.write(f"**Found by:** {fi['name']} ({fi['branch']})")
                            st.write(f"**Contact:** {fi['contact']}")


# ==================== BROWSE ITEMS ====================
elif page == "📋 Browse Items":
    st.subheader("📋 Browse all items")

    col1, col2, col3 = st.columns(3)
    with col1:
        f_type = st.selectbox("Type", ["All", "Lost", "Found"])
    with col2:
        f_cat = st.selectbox("Category", ["All"] + CATEGORIES)
    with col3:
        f_status = st.selectbox("Status", ["All", "Open", "Returned"])

    type_filter = None if f_type == "All" else f_type.lower()
    cat_filter = None if f_cat == "All" else f_cat
    status_filter = None if f_status == "All" else f_status.lower()

    items = get_items(item_type=type_filter, category=cat_filter, status=status_filter)
    st.caption(f"{len(items)} item(s) found")

    if not items:
        st.info("Nothing matches these filters yet.")
    for item in items:
        render_item_card(item)
