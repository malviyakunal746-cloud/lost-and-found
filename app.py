# app.py
import streamlit as st
import os
from datetime import datetime
from db import (
    add_item,
    get_items,
    get_item_by_id,
    update_item_status,
    add_claim,
    approve_claim,
    get_stats,
)
from matching import find_matches, calculate_match_score


# Page config
st.set_page_config(page_title="College Lost & Found", page_icon="🔍", layout="wide")


# Sidebar navigation
st.sidebar.title("🔍 Lost & Found")
page = st.sidebar.radio(
    "Navigate",
    [
        "📊 Dashboard",
        "📍 Report Found Item",
        "📢 Report Lost Item",
        "📋 Browse Items",
        "✅ My Claims",
    ],
)


# Helper function to save uploaded file
def save_upload(uploaded_file, item_type):
    if uploaded_file:
        # Create folder if not exists
        folder = f"uploads/{item_type}"
        os.makedirs(folder, exist_ok=True)

        # Save file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}_{uploaded_file.name}"
        filepath = os.path.join(folder, filename)

        with open(filepath, "wb") as f:
            f.write(uploaded_file.getvalue())

        return filepath
    return None


# ==================== DASHBOARD ====================
if page == "📊 Dashboard":
    st.title("📊 Lost & Found Dashboard")

    stats = get_stats()

    # Metrics row
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Total Lost Items", stats["total_lost"])

    with col2:
        st.metric("Total Found Items", stats["total_found"])

    with col3:
        st.metric("Items Returned", stats["total_returned"])

    with col4:
        st.metric("Return Rate", f"{stats['return_rate']}%")

    # Info box
    st.info(f"⏳ Pending Claims: {stats['pending_claims']}")

    # How it works
    st.subheader("📈 How It Works")
    st.markdown("""
    1. **Found something?** → Report it with details + photo
    2. **Lost something?** → Report it, we'll auto-match with found items
    3. **Claim an item?** → Provide verification details only owner would know
    4. **Track resolutions** → See how many items are being returned!
    """)


# ==================== REPORT FOUND ITEM ====================
elif page == "📍 Report Found Item":
    st.title("📍 Report Found Item")
    st.write("Fill in the details to report a found item.")

    with st.form("found_form", clear_on_submit=True):
        col1, col2 = st.columns(2)

        with col1:
            category = st.selectbox(
                "Category",
                ["Electronics", "Books", "Clothing", "Accessories", "Stationery", "Other"],
            )

            # Show custom item input if "Other" selected
            if category == "Other":
                custom_item = st.text_input(
                    "Item Name",
                    placeholder="Write your item name...",
                )
            else:
                custom_item = None

            location = st.text_input(
                "Where did you find it?", placeholder="e.g., Library, Canteen"
            )
            date_found = st.date_input("Date Found", value=datetime.now())

        with col2:
            name = st.text_input("Your Name *", placeholder="Full name")
            branch = st.selectbox(
                "Branch *",
                [
                    "CSE",
                    "IT",
                    "ECE",
                    "EEE",
                    "Mechanical",
                    "Civil",
                    "Business",
                    "MBA",
                    "BBA",
                ],
            )
            section = st.text_input("Section (optional)", placeholder="e.g., A, B, C")
            contact = st.text_input("Contact Number *", placeholder="10-digit mobile")
            email = st.text_input("Email (optional)", placeholder="college@email.com")

        description = st.text_area(
            "Description *",
            placeholder="Describe the item (brand, color, model, size, any unique marks...)\n\nExample: 'Blue Casio analog watch, black strap, small scratch on glass'",
        )

        image = st.file_uploader(
            "Upload Photo (optional but recommended)", type=["jpg", "jpeg", "png"]
        )

        submitted = st.form_submit_button("Submit Found Report", type="primary")

        if submitted:
            # Validation
            if not all([category, location, name, branch, contact, description]):
                st.error("Please fill all required fields (marked with *)")
            elif category == "Other" and not custom_item:
                st.error(
                    "Please specify what item it is when selecting 'Other' category"
                )
            else:
                # Combine category + custom_item for better matching
                final_category = f"Other: {custom_item}" if custom_item else category

                # Save image
                image_path = save_upload(image, "found")

                # Add to database
                item_id = add_item(
                    item_type="found",
                    category=final_category,
                    description=description,
                    location=location,
                    date_lost_found=date_found.isoformat(),
                    name=name,
                    branch=branch,
                    section=section,
                    contact=contact,
                    email=email,
                    image_path=image_path,
                )

                st.success(f"✅ Found item reported successfully! (ID: {item_id})")

                # Check for matching lost items
                lost_items = get_items(item_type="lost", status="open")
                matches = []

                for lost_item in lost_items:
                    score = calculate_match_score(
                        lost_item,
                        {
                            "category": final_category,
                            "description": description,
                            "location": location,
                        },
                    )
                    if score >= 70:
                        matches.append((lost_item, score))

                if matches:
                    st.subheader("🎯 Possible Matches Found!")
                    for lost_item, score in matches[:3]:  # Show top 3
                        with st.expander(
                            f"Match: {score}% - {lost_item['description'][:50]}..."
                        ):
                            st.write(f"**Category:** {lost_item['category']}")
                            st.write(f"**Location:** {lost_item['location']}")
                            st.write(
                                f"**Reported by:** {lost_item['name']} ({lost_item['branch']})"
                            )
                            st.write(f"**Contact:** {lost_item['contact']}")
                            if lost_item.get("image_path") and os.path.exists(
                                lost_item["image_path"]
                            ):
                                st.image(lost_item["image_path"], width=200)


# ==================== REPORT LOST ITEM ====================
elif page == "📢 Report Lost Item":
    st.title("📢 Report Lost Item")
    st.write("Fill in the details to report a lost item.")

    with st.form("lost_form", clear_on_submit=True):
        col1, col2 = st.columns(2)

        with col1:
            category = st.selectbox(
                "Category",
                ["Electronics", "Books", "Clothing", "Accessories", "Stationery", "Other"],
            )

            # Show custom item input if "Other" selected
            if category == "Other":
                custom_item = st.text_input(
                    "Item Name",
                    placeholder="Write your item name...",
                )
            else:
                custom_item = None

            location = st.text_input(
                "Where did you lose it?", placeholder="e.g., Library, Canteen"
            )
            date_lost = st.date_input("Date Lost", value=datetime.now())

        with col2:
            name = st.text_input("Your Name *", placeholder="Full name")
            branch = st.selectbox(
                "Branch *",
                [
                    "CSE",
                    "IT",
                    "ECE",
                    "EEE",
                    "Mechanical",
                    "Civil",
                    "Business",
                    "MBA",
                    "BBA",
                ],
            )
            section = st.text_input("Section (optional)", placeholder="e.g., A, B, C")
            contact = st.text_input("Contact Number *", placeholder="10-digit mobile")
            email = st.text_input("Email (optional)", placeholder="college@email.com")

        description = st.text_area(
            "Description *",
            placeholder="Describe the item (brand, color, model, size, any unique marks...)\n\nExample: 'Blue Casio analog watch, black strap, small scratch on glass'",
        )

        image = st.file_uploader(
            "Upload Photo (optional but recommended)", type=["jpg", "jpeg", "png"]
        )

        submitted = st.form_submit_button("Submit Lost Report", type="primary")

        if submitted:
            # Validation
            if not all([category, location, name, branch, contact, description]):
                st.error("Please fill all required fields (marked with *)")
            elif category == "Other" and not custom_item:
                st.error(
                    "Please specify what item it is when selecting 'Other' category"
                )
            else:
                # Combine category + custom_item for better matching
                final_category = f"Other: {custom_item}" if custom_item else category

                # Save image
                image_path = save_upload(image, "lost")

                # Add to database
                item_id = add_item(
                    item_type="lost",
                    category=final_category,
                    description=description,
                    location=location,
                    date_lost_found=date_lost.isoformat(),
                    name=name,
                    branch=branch,
                    section=section,
                    contact=contact,
                    email=email,
                    image_path=image_path,
                )

                st.success(f"✅ Lost item reported successfully! (ID: {item_id})")

                # Check for matching found items
                found_items = get_items(item_type="found", status="open")
                matches = []

                for found_item in found_items:
                    score = calculate_match_score(
                        {
                            "category": final_category,
                            "description": description,
                            "location": location,
                        },
                        found_item,
                    )
                    if score >= 70:
                        matches.append((found_item, score))

                if matches:
                    st.subheader("🎯 Possible Matches Found!")
                    for found_item, score in matches[:3]:  # Show top 3
                        with st.expander(
                            f"Match: {score}% - {found_item['description'][:50]}..."
                        ):
                            st.write(f"**Category:** {found_item['category']}")
                            st.write(f"**Location:** {found_item['location']}")
                            st.write(
                                f"**Found by:** {found_item['name']} ({found_item['branch']})"
                            )
                            st.write(f"**Contact:** {found_item['contact']}")
                            if found_item.get("image_path") and os.path.exists(
                                found_item["image_path"]
                            ):
                                st.image(found_item["image_path"], width=200)


# ==================== BROWSE ITEMS ====================
elif page == "📋 Browse Items":
    st.title("📋 Browse All Items")

    # Filter options
    col1, col2, col3 = st.columns(3)

    with col1:
        item_type = st.selectbox("Type", ["All", "Lost", "Found"])

    with col2:
        category = st.selectbox(
            "Category",
            [
                "All",
                "Electronics",
                "Books",
                "Clothing",
                "Accessories",
                "Stationery",
                "Other",
            ],
        )

    with col3:
        status = st.selectbox("Status", ["All", "Open", "Returned"])

    # Build query
    type_filter = None if item_type == "All" else item_type.lower()
    cat_filter = None if category == "All" else category
    status_filter = None if status == "All" else status.lower()

    if type_filter == "lost":
        type_filter = "lost"
    elif type_filter == "found":
        type_filter = "found"
    else:
        type_filter = None

    items = get_items(item_type=type_filter, category=cat_filter, status=status_filter)

    st.write(f"Found {len(items)} items")

    # Display items
    for item in items:
        with st.expander(
            f"{item['type'].upper()}: {item['description'][:60]}... ({item['category']})"
        ):
            col1, col2 = st.columns([2, 1])

            with col1:
                st.write(f"**Description:** {item['description']}")
                st.write(f"**Location:** {item['location']}")
                st.write(f"**Date:** {item['date_lost_found']}")
                st.write(
                    f"**Reported by:** {item['name']} ({item['branch']}, {item['section']})"
                )
                st.write(f"**Contact:** {item['contact']}")
                if item.get("email"):
                    st.write(f"**Email:** {item['email']}")
                st.write(f"**Status:** {item['status']}")

            with col2:
                if item.get("image_path") and os.path.exists(item["image_path"]):
                    st.image(item["image_path"], width=200)
                else:
                    st.info("No photo")


# ==================== MY CLAIMS ====================
elif page == "✅ My Claims":
    st.title("✅ Claims & Resolutions")
    st.info("This page will show your submitted claims and their status. (Coming soon)")

    # Placeholder for future implementation
    st.write("Track the status of your claims here.")