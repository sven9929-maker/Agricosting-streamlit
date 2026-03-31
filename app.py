"""
AgriCosting Pro — Streamlit Edition
Agricultural Outgrower Input Costing, FX Reconciliation & Dashboard
"""

import streamlit as st
import pandas as pd
import io
from datetime import date

st.set_page_config(
    page_title="AgriCosting Pro",
    page_icon="🌾",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
[data-testid="stSidebar"] { background-color: #161b22; }
.block-container { padding-top: 1.5rem; }
.metric-card {
    background: #161b22; border: 1px solid #30363d;
    border-radius: 10px; padding: 16px 20px; margin-bottom: 8px;
}
.metric-label { font-size: 11px; color: #6e7681; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 4px; }
.metric-value { font-size: 24px; font-weight: 700; font-family: monospace; }
.metric-sub   { font-size: 11px; color: #8b949e; margin-top: 4px; }
.green  { color: #3fb950; }
.blue   { color: #58a6ff; }
.amber  { color: #ffa657; }
.red    { color: #f78166; }
.purple { color: #d2a8ff; }
.info-box {
    background: rgba(88,166,255,.08); border: 1px solid rgba(88,166,255,.25);
    border-radius: 8px; padding: 10px 14px; font-size: 13px; color: #58a6ff; margin-bottom: 12px;
}
</style>
""", unsafe_allow_html=True)

# ── SESSION STATE INIT ────────────────────────────────────────────────────────
def init_state():
    if "items" not in st.session_state:
        st.session_state.items = [
            {"id":1,"code":"FERT-01","name":"NPK Fertilizer","category":"Fertilizer","type":"markup","markup":15.0,"uom":"50kg bag"},
            {"id":2,"code":"CHEM-01","name":"Pesticide A","category":"Chemicals","type":"markup","markup":12.0,"uom":"Litre"},
            {"id":3,"code":"SEED-01","name":"Tobacco Seed","category":"Seed","type":"markup","markup":20.0,"uom":"Pack"},
            {"id":4,"code":"HESS-01","name":"Hessian Bags","category":"Packaging","type":"recovery","markup":0.0,"uom":"Each"},
            {"id":5,"code":"PAPER-01","name":"Tobacco Paper","category":"Packaging","type":"recovery","markup":0.0,"uom":"Ream"},
            {"id":6,"code":"FUEL-01","name":"Diesel","category":"Fuel","type":"markup","markup":8.0,"uom":"Litre"},
            {"id":7,"code":"TWINE-01","name":"Baling Twine","category":"Packaging","type":"recovery","markup":0.0,"uom":"Roll"},
        ]
    if "pricing" not in st.session_state:
        st.session_state.pricing = [
            {"id":1,"item_id":1,"cost_usd":18.50,"fx_rate":27.0,"markup_pct":15.0,"qty":500},
            {"id":2,"item_id":2,"cost_usd":12.00,"fx_rate":27.0,"markup_pct":12.0,"qty":200},
            {"id":3,"item_id":4,"cost_usd":3.20, "fx_rate":27.0,"markup_pct":0.0, "qty":1000},
            {"id":4,"item_id":6,"cost_usd":1.45, "fx_rate":27.0,"markup_pct":8.0, "qty":2000},
        ]
    if "invoices" not in st.session_state:
        st.session_state.invoices = [
            {"id":1,"item_id":1,"supplier":"ZamFert Ltd","number":"INV-2025-001","date":"2025-02-10","currency":"USD","gross":9500.0,"vat":950.0,"vat_rec":True,"qty":500},
            {"id":2,"item_id":2,"supplier":"AgroChems","number":"INV-2025-002","date":"2025-02-15","currency":"USD","gross":2500.0,"vat":250.0,"vat_rec":True,"qty":200},
            {"id":3,"item_id":4,"supplier":"PackZam","number":"INV-2025-003","date":"2025-02-18","currency":"ZMW","gross":82000.0,"vat":8200.0,"vat_rec":False,"qty":1000},
            {"id":4,"item_id":6,"supplier":"FuelDirect","number":"INV-2025-004","date":"2025-03-01","currency":"USD","gross":2950.0,"vat":295.0,"vat_rec":True,"qty":2000},
        ]
    if "actuals" not in st.session_state:
        st.session_state.actuals = [
            {"id":1,"item_id":1,"sage_doc":"SAGE-2025-0041","post_date":"2025-02-20","amount_zmw":256500.0,"qty":500},
            {"id":2,"item_id":2,"sage_doc":"SAGE-2025-0042","post_date":"2025-02-22","amount_zmw":67000.0,"qty":200},
            {"id":3,"item_id":4,"sage_doc":"SAGE-2025-0043","post_date":"2025-02-25","amount_zmw":82000.0,"qty":1000},
        ]
    if "fx" not in st.session_state:
        st.session_state.fx = {"purchase": 26.5, "pricing": 27.0, "reporting": 27.2}
    if "season" not in st.session_state:
        st.session_state.season = "2025"
    if "next_id" not in st.session_state:
        st.session_state.next_id = 20

init_state()

def nid():
    st.session_state.next_id += 1
    return st.session_state.next_id

def get_item(item_id):
    return next((i for i in st.session_state.items if i["id"] == item_id), {})

def fmt_usd(v): return f"${float(v or 0):,.2f}"
def fmt_zmw(v): return f"K{float(v or 0):,.2f}"
def fmt_n(v, d=2): return f"{float(v or 0):,.{d}f}"

def calc_selling(item_type, cost, markup_pct):
    return cost if item_type == "recovery" else cost * (1 + markup_pct / 100)

def calc_pricing(p):
    item = get_item(p["item_id"])
    cost = p["cost_usd"]
    rfx  = st.session_state.fx["reporting"]
    selling = calc_selling(item.get("type","markup"), cost, p["markup_pct"])
    margin  = 0 if item.get("type") == "recovery" else selling - cost
    return {
        "cost_zmw":     cost * p["fx_rate"],
        "selling_usd":  selling,
        "selling_zmw":  selling * rfx,
        "margin_unit":  margin,
        "total_margin": margin * p["qty"],
        "total_rev":    selling * p["qty"],
        "margin_pct":   (margin / selling * 100) if selling > 0 else 0,
    }

def calc_invoice(inv):
    net = inv["gross"] if inv["vat_rec"] else inv["gross"] + inv["vat"]
    pfx = st.session_state.fx["purchase"]
    return {
        "net":    net,
        "cpu":    net / inv["qty"] if inv["qty"] > 0 else 0,
        "usd_eq": inv["gross"] if inv["currency"] == "USD" else net / pfx,
    }

def calc_actual(a):
    rfx = st.session_state.fx["reporting"]
    inv = next((i for i in st.session_state.invoices if i["item_id"] == a["item_id"] and i["currency"] == "USD"), None)
    return {
        "cpu_zmw":     a["amount_zmw"] / a["qty"] if a["qty"] > 0 else 0,
        "cost_usd":    a["amount_zmw"] / rfx if rfx > 0 else 0,
        "implied_fx":  (a["amount_zmw"] / inv["gross"]) if inv and inv["gross"] > 0 else None,
        "matched_inv": inv,
    }

def get_dashboard_metrics():
    rfx = st.session_state.fx["reporting"]
    total_rev = total_comm_margin = total_actual_zmw = 0
    for p in st.session_state.pricing:
        c = calc_pricing(p)
        total_rev          += c["total_rev"]
        total_comm_margin  += c["total_margin"]
    for a in st.session_state.actuals:
        total_actual_zmw += a["amount_zmw"]
    actual_cost_usd = total_actual_zmw / rfx if rfx > 0 else 0
    actual_margin   = total_rev - actual_cost_usd
    return {
        "revenue":          total_rev,
        "comm_margin":      total_comm_margin,
        "actual_margin":    actual_margin,
        "variance":         total_comm_margin - actual_margin,
        "actual_cost_usd":  actual_cost_usd,
    }

def metric_card(label, value, sub="", color="blue"):
    st.markdown(f"""
    <div class="metric-card">
      <div class="metric-label">{label}</div>
      <div class="metric-value {color}">{value}</div>
      {"<div class='metric-sub'>"+sub+"</div>" if sub else ""}
    </div>""", unsafe_allow_html=True)

# ── SIDEBAR ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🌾 AgriCosting Pro")
    st.caption("Outgrower Finance System")
    st.session_state.season = st.selectbox("Season", ["2024","2025","2026"],
        index=["2024","2025","2026"].index(st.session_state.season))
    st.divider()
    page = st.radio("Navigation", [
        "📊 Dashboard",
        "📦 Input Master",
        "💰 Commercial Pricing",
        "🧾 Invoice Capture",
        "📋 Sage Actuals",
        "💱 FX Rates",
        "⚖️ Reconciliation",
        "📈 Reports",
    ])
    st.divider()
    fx = st.session_state.fx
    st.caption("CURRENT FX RATES")
    st.markdown(f"Purchase: `{fx['purchase']}`  \nPricing: `{fx['pricing']}`  \nReporting: `{fx['reporting']}`")

# ── DASHBOARD ─────────────────────────────────────────────────────────────────
if page == "📊 Dashboard":
    st.title(f"📊 Executive Dashboard — {st.session_state.season} Season")
    m   = get_dashboard_metrics()
    rfx = st.session_state.fx["reporting"]
    comm_pct = (m["comm_margin"] / m["revenue"] * 100) if m["revenue"] > 0 else 0

    c1, c2, c3, c4 = st.columns(4)
    with c1: metric_card("Total Revenue",      fmt_usd(m["revenue"]),       "Commercial selling value", "blue")
    with c2: metric_card("Commercial Margin",  fmt_usd(m["comm_margin"]),   f"{fmt_n(comm_pct)}% margin", "green")
    with c3: metric_card("Actual Margin",      fmt_usd(m["actual_margin"]), "Post Sage reconciliation", "amber")
    sign = "▲" if m["variance"] >= 0 else "▼"
    with c4: metric_card("FX / Proc Variance", f"{sign} {fmt_usd(abs(m['variance']))}", "vs commercial expectation", "green" if m["variance"] >= 0 else "red")

    st.divider()
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("#### Margin Waterfall (USD)")
        wf = pd.DataFrame({
            "Metric": ["Revenue","Comm Margin","Actual Margin","FX/Proc Var"],
            "USD":    [m["revenue"], m["comm_margin"], m["actual_margin"], m["variance"]],
        })
        st.bar_chart(wf.set_index("Metric"))

    with c2:
        st.markdown("#### FX Rates Comparison")
        fx_df = pd.DataFrame({
            "Rate Type": ["Purchase FX","Pricing FX","Reporting FX"],
            "ZMW/USD":   [fx["purchase"], fx["pricing"], fx["reporting"]],
        })
        st.bar_chart(fx_df.set_index("Rate Type"))

    st.divider()
    st.markdown("#### Category Breakdown")
    rows = []
    for p in st.session_state.pricing:
        item   = get_item(p["item_id"])
        c      = calc_pricing(p)
        actual = next((a for a in st.session_state.actuals if a["item_id"] == p["item_id"]), None)
        act_cost = variance = None
        if actual:
            ac       = calc_actual(actual)
            act_cost = ac["cost_usd"]
            variance = c["total_margin"] - (c["total_rev"] - act_cost)
        rows.append({
            "Item":             item.get("name","—"),
            "Type":             item.get("type","—"),
            "Revenue USD":      fmt_usd(c["total_rev"]),
            "Comm Margin USD":  fmt_usd(c["total_margin"]),
            "Margin %":         f"{fmt_n(c['margin_pct'])}%",
            "Actual Cost USD":  fmt_usd(act_cost) if act_cost is not None else "—",
            "FX/Proc Variance": (("▲ " if variance >= 0 else "▼ ") + fmt_usd(abs(variance))) if variance is not None else "—",
        })
    if rows:
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

# ── INPUT MASTER ──────────────────────────────────────────────────────────────
elif page == "📦 Input Master":
    st.title("📦 Input Master Data")
    st.caption(f"{len(st.session_state.items)} items registered")

    with st.expander("➕ Add New Item"):
        with st.form("add_item"):
            c1, c2 = st.columns(2)
            with c1:
                code      = st.text_input("Item Code *", placeholder="e.g. FERT-02")
                name      = st.text_input("Item Name *", placeholder="e.g. Urea Fertilizer")
                category  = st.selectbox("Category", ["Fertilizer","Chemicals","Seed","Packaging","Fuel","Inputs"])
            with c2:
                itype     = st.selectbox("Input Type", ["markup","recovery"])
                markup    = st.number_input("Default Markup %", 0.0, 100.0, 0.0, 0.5)
                uom       = st.text_input("Unit of Measure", placeholder="e.g. 50kg bag")
            if st.form_submit_button("Save Item", type="primary"):
                if not code or not name:
                    st.error("Code and name are required")
                elif any(i["code"] == code for i in st.session_state.items):
                    st.error(f"Code '{code}' already exists")
                else:
                    st.session_state.items.append({"id":nid(),"code":code,"name":name,"category":category,"type":itype,"markup":markup,"uom":uom})
                    st.success(f"'{name}' saved!")
                    st.rerun()

    st.divider()
    df = pd.DataFrame([{
        "Code": i["code"], "Name": i["name"], "Category": i["category"],
        "Type": i["type"],
        "Default Markup": f"{i['markup']}%" if i["type"]=="markup" else "—",
        "UoM": i["uom"],
    } for i in st.session_state.items])
    st.dataframe(df, use_container_width=True, hide_index=True)

    st.divider()
    names = [f"{i['code']} — {i['name']}" for i in st.session_state.items]
    to_del = st.selectbox("Remove item", ["— select —"] + names)
    if st.button("🗑 Remove") and to_del != "— select —":
        code_del = to_del.split(" — ")[0]
        st.session_state.items = [i for i in st.session_state.items if i["code"] != code_del]
        st.success("Removed"); st.rerun()

# ── COMMERCIAL PRICING ────────────────────────────────────────────────────────
elif page == "💰 Commercial Pricing":
    st.title("💰 Commercial Pricing")

    with st.expander("➕ Add / Replace Pricing"):
        with st.form("add_pricing"):
            opts = {f"{i['name']} ({i['type']})": i["id"] for i in st.session_state.items}
            c1, c2, c3 = st.columns(3)
            with c1:
                sel   = st.selectbox("Item", list(opts.keys()))
                cost  = st.number_input("Commercial Cost USD", 0.01, value=10.0, step=0.01)
            with c2:
                fxr   = st.number_input("Pricing FX Rate", value=st.session_state.fx["pricing"], step=0.001, format="%.3f")
                mkup  = st.number_input("Markup %", 0.0, 100.0, 0.0, 0.5)
            with c3:
                qty   = st.number_input("Quantity", 1.0, value=100.0, step=1.0)

            item_id = opts[sel]
            item    = get_item(item_id)
            selling = calc_selling(item.get("type","markup"), cost, mkup)
            margin  = 0 if item.get("type")=="recovery" else selling - cost
            st.info(f"**Preview** → Selling: {fmt_usd(selling)} | Margin/unit: {fmt_usd(margin)} | Total margin: {fmt_usd(margin*qty)}")

            if st.form_submit_button("Save Pricing", type="primary"):
                st.session_state.pricing = [p for p in st.session_state.pricing if p["item_id"] != item_id]
                st.session_state.pricing.append({"id":nid(),"item_id":item_id,"cost_usd":cost,"fx_rate":fxr,"markup_pct":mkup,"qty":qty})
                st.success("Pricing saved!"); st.rerun()

    st.divider()
    rows = []
    for p in st.session_state.pricing:
        item = get_item(p["item_id"])
        c    = calc_pricing(p)
        rows.append({
            "Item": item.get("name","—"), "Type": item.get("type","—"),
            "Cost USD":       fmt_usd(p["cost_usd"]),
            "Cost ZMW":       fmt_zmw(c["cost_zmw"]),
            "Markup %":       f"{fmt_n(p['markup_pct'])}%" if item.get("type")!="recovery" else "—",
            "Selling USD":    fmt_usd(c["selling_usd"]),
            "Selling ZMW":    fmt_zmw(c["selling_zmw"]),
            "Margin/Unit":    fmt_usd(c["margin_unit"]),
            "Total Margin":   fmt_usd(c["total_margin"]),
            "Margin %":       f"{fmt_n(c['margin_pct'])}%",
            "Qty":            f"{int(p['qty']):,}",
        })
    if rows:
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    else:
        st.info("No pricing records yet.")

# ── INVOICES ──────────────────────────────────────────────────────────────────
elif page == "🧾 Invoice Capture":
    st.title("🧾 Invoice Capture")

    with st.expander("➕ Capture New Invoice"):
        with st.form("add_invoice"):
            opts = {i["name"]: i["id"] for i in st.session_state.items}
            c1, c2, c3 = st.columns(3)
            with c1:
                sel      = st.selectbox("Item", list(opts.keys()))
                supplier = st.text_input("Supplier *")
                inv_num  = st.text_input("Invoice Number *", placeholder="INV-2025-XXX")
            with c2:
                inv_date = st.date_input("Invoice Date", value=date.today())
                currency = st.selectbox("Currency", ["USD","ZMW"])
                gross    = st.number_input("Gross Amount", 0.01, value=1000.0, step=0.01)
            with c3:
                vat     = st.number_input("VAT Amount", 0.0, value=0.0, step=0.01)
                vat_rec = st.selectbox("VAT Recoverable?", ["Yes","No"]) == "Yes"
                qty     = st.number_input("Quantity", 0.01, value=1.0)

            if st.form_submit_button("Save Invoice", type="primary"):
                if not supplier or not inv_num:
                    st.error("Supplier and invoice number required")
                else:
                    st.session_state.invoices.append({
                        "id":nid(),"item_id":opts[sel],"supplier":supplier,"number":inv_num,
                        "date":str(inv_date),"currency":currency,"gross":gross,
                        "vat":vat,"vat_rec":vat_rec,"qty":qty,
                    })
                    st.success("Invoice captured!"); st.rerun()

    st.divider()
    rows = []
    for inv in st.session_state.invoices:
        item = get_item(inv["item_id"])
        c    = calc_invoice(inv)
        rows.append({
            "Invoice #": inv["number"], "Supplier": inv["supplier"],
            "Item": item.get("name","—"), "Date": inv["date"],
            "Ccy": inv["currency"], "Gross": fmt_n(inv["gross"]),
            "VAT Rec?": "Yes" if inv["vat_rec"] else "No",
            "Net Cost": fmt_n(c["net"]), "Cost/Unit": fmt_n(c["cpu"],4),
            "USD Equiv": fmt_usd(c["usd_eq"]),
        })
    if rows:
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    else:
        st.info("No invoices yet.")

# ── SAGE ACTUALS ──────────────────────────────────────────────────────────────
elif page == "📋 Sage Actuals":
    st.title("📋 Sage Actual Costs")
    st.markdown('<div class="info-box">ℹ️ When a ZMW actual is matched to a USD invoice, Implied FX is auto-calculated: Sage ZMW ÷ Invoice USD</div>', unsafe_allow_html=True)

    with st.expander("➕ Capture Sage Actual"):
        with st.form("add_actual"):
            opts = {i["name"]: i["id"] for i in st.session_state.items}
            c1, c2, c3 = st.columns(3)
            with c1:
                sel      = st.selectbox("Item", list(opts.keys()))
                sage_doc = st.text_input("Sage Document #*", placeholder="SAGE-2025-XXXX")
            with c2:
                post_date  = st.date_input("Posting Date", value=date.today())
                amount_zmw = st.number_input("Sage Amount (ZMW)", 0.01, value=1000.0, step=0.01)
            with c3:
                qty = st.number_input("Quantity", 0.01, value=1.0)

            if st.form_submit_button("Save Actual", type="primary"):
                if not sage_doc:
                    st.error("Sage document number required")
                else:
                    st.session_state.actuals.append({
                        "id":nid(),"item_id":opts[sel],"sage_doc":sage_doc,
                        "post_date":str(post_date),"amount_zmw":amount_zmw,"qty":qty,
                    })
                    st.success("Actual saved!"); st.rerun()

    st.divider()
    rows = []
    for a in st.session_state.actuals:
        item = get_item(a["item_id"])
        c    = calc_actual(a)
        rows.append({
            "Sage Doc": a["sage_doc"], "Item": item.get("name","—"),
            "Post Date": a["post_date"], "Amount ZMW": fmt_zmw(a["amount_zmw"]),
            "Qty": f"{int(a['qty']):,}", "Cost/Unit ZMW": fmt_zmw(c["cpu_zmw"]),
            "Cost USD Equiv": fmt_usd(c["cost_usd"]),
            "Implied FX": fmt_n(c["implied_fx"],4) if c["implied_fx"] else "—",
            "Invoice Match": c["matched_inv"]["number"] if c["matched_inv"] else "No match",
        })
    if rows:
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    else:
        st.info("No actuals yet.")

# ── FX RATES ──────────────────────────────────────────────────────────────────
elif page == "💱 FX Rates":
    st.title("💱 FX Rate Management")
    st.caption("ZMW per USD · All three rates drive different parts of the calculation engine")

    fx     = st.session_state.fx
    spread = fx["reporting"] - fx["purchase"]

    c1, c2, c3, c4 = st.columns(4)
    with c1: metric_card("Purchase FX",  fmt_n(fx["purchase"],4),  "Rate at invoice date",   "purple")
    with c2: metric_card("Pricing FX",   fmt_n(fx["pricing"],4),   "Rate for selling price", "blue")
    with c3: metric_card("Reporting FX", fmt_n(fx["reporting"],4), "ZMW conversion rate",    "green")
    with c4: metric_card("FX Spread",    fmt_n(spread,4),          "Reporting vs Purchase",  "amber")

    st.divider()
    st.markdown("#### Update FX Rates")
    with st.form("fx_form"):
        c1, c2, c3 = st.columns(3)
        with c1: new_p  = st.number_input("Purchase FX",  value=fx["purchase"],  step=0.001, format="%.4f")
        with c2: new_pr = st.number_input("Pricing FX",   value=fx["pricing"],   step=0.001, format="%.4f")
        with c3: new_r  = st.number_input("Reporting FX", value=fx["reporting"], step=0.001, format="%.4f")
        if st.form_submit_button("Update All Rates", type="primary"):
            st.session_state.fx = {"purchase": new_p, "pricing": new_pr, "reporting": new_r}
            st.success("Rates updated — all calculations refreshed."); st.rerun()

    st.divider()
    st.markdown("#### FX Scenario Analysis")
    st.caption("Effect of ±2 ZMW shift on Reporting FX")
    orig = st.session_state.fx["reporting"]
    base_m = get_dashboard_metrics()
    scen_rows = []
    for delta in [-2.0, -1.0, 0.0, 1.0, 2.0]:
        st.session_state.fx["reporting"] = orig + delta
        sm = get_dashboard_metrics()
        diff = sm["actual_margin"] - base_m["actual_margin"]
        scen_rows.append({
            "Reporting FX":     fmt_n(orig + delta, 3),
            "Actual Margin USD": fmt_usd(sm["actual_margin"]),
            "FX/Proc Var USD":  fmt_usd(sm["variance"]),
            "vs Base":          "← Base" if delta == 0 else (("▲ " if diff >= 0 else "▼ ") + fmt_usd(abs(diff))),
        })
    st.session_state.fx["reporting"] = orig
    st.dataframe(pd.DataFrame(scen_rows), use_container_width=True, hide_index=True)

# ── RECONCILIATION ────────────────────────────────────────────────────────────
elif page == "⚖️ Reconciliation":
    st.title("⚖️ Reconciliation")
    st.caption("Commercial vs Actual · FX & Procurement Variance Bridge")
    st.markdown('<div class="info-box">ℹ️ Recovery/Rental items use Selling Value − Actual Cost to avoid distorting markup dashboards.</div>', unsafe_allow_html=True)

    rfx    = st.session_state.fx["reporting"]
    rows   = []
    totals = {"rev":0.0, "comm_margin":0.0, "actual_margin":0.0, "variance":0.0}

    for p in st.session_state.pricing:
        item   = get_item(p["item_id"])
        c      = calc_pricing(p)
        actual = next((a for a in st.session_state.actuals if a["item_id"] == p["item_id"]), None)
        act_cost = act_margin = var_usd = var_zmw = impl_fx = None
        if actual:
            ac        = calc_actual(actual)
            act_cost  = ac["cost_usd"]
            act_margin= c["total_rev"] - act_cost
            var_usd   = c["total_margin"] - act_margin
            var_zmw   = var_usd * rfx
            impl_fx   = ac["implied_fx"]
            totals["actual_margin"] += act_margin
            totals["variance"]      += var_usd
        totals["rev"]         += c["total_rev"]
        totals["comm_margin"] += c["total_margin"]
        rows.append({
            "Item":             item.get("name","—"),
            "Type":             item.get("type","—"),
            "Total Revenue":    fmt_usd(c["total_rev"]),
            "Comm Margin USD":  fmt_usd(c["total_margin"]),
            "Actual Cost USD":  fmt_usd(act_cost)  if act_cost  is not None else "—",
            "Actual Margin USD":fmt_usd(act_margin) if act_margin is not None else "—",
            "FX/Proc Var USD":  (("▲ " if var_usd>=0 else "▼ ")+fmt_usd(abs(var_usd))) if var_usd is not None else "—",
            "FX/Proc Var ZMW":  fmt_zmw(var_zmw) if var_zmw is not None else "—",
            "Implied FX":       fmt_n(impl_fx,4)  if impl_fx  is not None else "—",
        })

    if rows:
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    st.divider()
    st.markdown("#### Summary Totals")
    c1, c2, c3, c4 = st.columns(4)
    with c1: metric_card("Total Revenue",  fmt_usd(totals["rev"]),          color="blue")
    with c2: metric_card("Comm Margin",    fmt_usd(totals["comm_margin"]),  color="green")
    with c3: metric_card("Actual Margin",  fmt_usd(totals["actual_margin"]),color="amber")
    s = "▲" if totals["variance"] >= 0 else "▼"
    with c4: metric_card("FX/Proc Var",   f"{s} {fmt_usd(abs(totals['variance']))}",color="green" if totals["variance"]>=0 else "red")

# ── REPORTS ───────────────────────────────────────────────────────────────────
elif page == "📈 Reports":
    st.title(f"📈 Reports — {st.session_state.season} Season")

    m       = get_dashboard_metrics()
    rfx     = st.session_state.fx["reporting"]
    fx      = st.session_state.fx
    comm_cost   = m["revenue"] - m["comm_margin"]
    actual_cost = m["revenue"] - m["actual_margin"]

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("#### USD Summary")
        st.dataframe(pd.DataFrame({
            "Line Item": ["Total Revenue USD","Commercial Cost USD","Commercial Margin USD",
                          "Actual Cost USD (Sage)","Actual Margin USD","FX / Proc Variance USD"],
            "Amount":    [fmt_usd(m["revenue"]), f"({fmt_usd(comm_cost)})",
                          fmt_usd(m["comm_margin"]), f"({fmt_usd(actual_cost)})",
                          fmt_usd(m["actual_margin"]),
                          ("▲ " if m["variance"]>=0 else "▼ ")+fmt_usd(abs(m["variance"]))],
        }), use_container_width=True, hide_index=True)

    with c2:
        st.markdown("#### ZMW Summary")
        st.dataframe(pd.DataFrame({
            "Line Item": ["Reporting FX Rate","Total Revenue ZMW","Commercial Cost ZMW",
                          "Commercial Margin ZMW","Actual Cost ZMW","Actual Margin ZMW","FX / Proc Var ZMW"],
            "Amount":    [fmt_n(rfx,3), fmt_zmw(m["revenue"]*rfx), f"({fmt_zmw(comm_cost*rfx)})",
                          fmt_zmw(m["comm_margin"]*rfx), f"({fmt_zmw(actual_cost*rfx)})",
                          fmt_zmw(m["actual_margin"]*rfx), fmt_zmw(m["variance"]*rfx)],
        }), use_container_width=True, hide_index=True)

    st.divider()
    st.markdown("#### FX Rate Summary")
    c1, c2, c3 = st.columns(3)
    with c1: metric_card("Purchase FX",  fmt_n(fx["purchase"],4),  "Invoice date rate",   "purple")
    with c2: metric_card("Pricing FX",   fmt_n(fx["pricing"],4),   "Selling price rate",  "blue")
    with c3: metric_card("Reporting FX", fmt_n(fx["reporting"],4), "ZMW conversion rate", "green")

    st.divider()
    st.markdown("#### Export")
    buf = io.StringIO()
    buf.write(f"AgriCosting Pro — {st.session_state.season} Season\n\n")
    buf.write(f"FX RATES\nPurchase,{fx['purchase']}\nPricing,{fx['pricing']}\nReporting,{fx['reporting']}\n\n")
    buf.write("PRICING SUMMARY\nItem,Type,Cost USD,Markup%,Selling USD,Total Margin USD\n")
    for p in st.session_state.pricing:
        item = get_item(p["item_id"])
        c    = calc_pricing(p)
        buf.write(f"{item.get('name','')},{item.get('type','')},{p['cost_usd']},{p['markup_pct']}%,{c['selling_usd']:.4f},{c['total_margin']:.2f}\n")
    buf.write("\nINVOICES\nInvoice#,Supplier,Item,Date,Currency,Gross,VAT Rec,Net,Cost/Unit\n")
    for inv in st.session_state.invoices:
        item = get_item(inv["item_id"])
        c    = calc_invoice(inv)
        buf.write(f"{inv['number']},{inv['supplier']},{item.get('name','')},{inv['date']},{inv['currency']},{inv['gross']},{'Yes' if inv['vat_rec'] else 'No'},{c['net']:.2f},{c['cpu']:.4f}\n")
    st.download_button("⬇️ Download CSV Report", buf.getvalue(),
        file_name=f"AgriCosting_{st.session_state.season}.csv", mime="text/csv")
