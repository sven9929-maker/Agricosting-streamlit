
import streamlit as st
import pandas as pd
import json
import copy

st.set_page_config(page_title="AgriCosting Pro", page_icon="🌾", layout="wide")

# ---------------- Session Init (FIXED) ----------------
if "items" not in st.session_state:
    st.session_state.items = []

if "pricing" not in st.session_state:
    st.session_state.pricing = []

if "invoices" not in st.session_state:
    st.session_state.invoices = []

if "actuals" not in st.session_state:
    st.session_state.actuals = []

if "fx" not in st.session_state:
    st.session_state.fx = {"reporting": 27}


DATA_FILE = "agricosting_data.json"

def load_data():
    try:
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    except:
        return {}

def save_data():
    data = {
        "items": st.session_state.get("items", []),
        "pricing": st.session_state.get("pricing", []),
        "invoices": st.session_state.get("invoices", []),
        "actuals": st.session_state.get("actuals", []),
        "fx": st.session_state.get("fx", {}),
    }
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)


page = st.sidebar.radio(
    "Navigation",
    ["Dashboard","Items","Pricing","Invoices","Actuals","FX"]
)

if st.sidebar.button("Save"):
    save_data()


# ---------------- Dashboard ----------------

if page == "Dashboard":
    st.title("AgriCosting Pro Dashboard")
    st.write("Items:", len(st.session_state.get("items", [])))
    st.write("Pricing:", len(st.session_state.get("pricing", [])))


# ---------------- Items ----------------

elif page == "Items":
    st.title("Items")

    name = st.text_input("Item Name")

    if st.button("Add Item"):
        st.session_state.items.append({
            "id": str(len(st.session_state.items)+1),
            "name": name,
            "type": "markup"
        })
        save_data()
        st.rerun()

    st.dataframe(pd.DataFrame(st.session_state.get("items", [])))


# ---------------- Pricing ----------------

elif page == "Pricing":
    st.title("Pricing")

    if st.session_state.items:

        item = st.selectbox(
            "Item",
            [i["name"] for i in st.session_state.items]
        )

        cost = st.number_input("Cost", 0.0)

        if st.button("Save Pricing"):
            st.session_state.pricing.append({
                "item": item,
                "cost": cost
            })
            save_data()
            st.rerun()

    st.dataframe(pd.DataFrame(st.session_state.get("pricing", [])))


# ---------------- Invoices ----------------

elif page == "Invoices":
    st.title("Invoices")

    supplier = st.text_input("Supplier")
    amount = st.number_input("Amount", 0.0)

    if st.button("Add Invoice"):
        st.session_state.invoices.append({
            "supplier": supplier,
            "amount": amount
        })
        save_data()
        st.rerun()

    st.dataframe(pd.DataFrame(st.session_state.get("invoices", [])))


# ---------------- Actuals ----------------

elif page == "Actuals":
    st.title("Actuals")

    amount = st.number_input("Amount", 0.0)

    if st.button("Add"):
        st.session_state.actuals.append({
            "amount": amount
        })
        save_data()
        st.rerun()

    st.dataframe(pd.DataFrame(st.session_state.get("actuals", [])))


# ---------------- FX ----------------

elif page == "FX":
    st.title("FX Rates")

    rate = st.number_input(
        "Reporting FX",
        value=float(st.session_state.fx["reporting"])
    )

    if st.button("Update FX"):
        st.session_state.fx["reporting"] = rate
        save_data()
        st.success("Updated")
