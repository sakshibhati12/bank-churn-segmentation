import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Bank Churn Dashboard", layout="wide")
st.title("Customer Segmentation & Churn Analytics - European Banking")

df = pd.read_csv("churn_clean.csv")

# ---- Sidebar filters ----
st.sidebar.header("Filters")

geo_options = sorted(df["Geography"].unique())
gender_options = sorted(df["Gender"].unique())
age_options = ["<30", "30-45", "46-60", "60+"]

geo_sel = st.sidebar.multiselect("Country", geo_options, default=geo_options)
gender_sel = st.sidebar.multiselect("Gender", gender_options, default=gender_options)
age_sel = st.sidebar.multiselect("Age group", age_options, default=age_options)

filtered = df[
    df["Geography"].isin(geo_sel)
    & df["Gender"].isin(gender_sel)
    & df["AgeGroup"].isin(age_sel)
]

if filtered.empty:
    st.warning("No customers match these filters. Please select at least one option in each filter.")
    st.stop()

# ---- KPIs ----
churn_rate = filtered["Exited"].mean() * 100

hv = filtered[filtered["HighValue"]]
hv_ratio = hv["Exited"].mean() * 100 if len(hv) > 0 else 0

col1, col2, col3 = st.columns(3)
col1.metric("Customers", f"{len(filtered):,}")
col2.metric("Churn Rate", f"{churn_rate:.2f}%")
col3.metric("High-Value Churn Ratio", f"{hv_ratio:.2f}%")
st.subheader("Churn rate by country")

by_geo = (
    filtered.groupby("Geography")["Exited"].mean().mul(100).reset_index()
    .rename(columns={"Exited": "Churn Rate (%)"})
)

fig_geo = px.bar(by_geo, x="Geography", y="Churn Rate (%)", text_auto=".1f")
st.plotly_chart(fig_geo, width="stretch")

st.subheader("Churn rate by age group and tenure")
left, right = st.columns(2)

tenure_order = ["New", "Mid-term", "Long-term"]

by_age = (
    filtered.groupby("AgeGroup")["Exited"].mean().mul(100).reset_index()
    .rename(columns={"Exited": "Churn Rate (%)"})
)
fig_age = px.bar(
    by_age, x="AgeGroup", y="Churn Rate (%)", text_auto=".1f",
    category_orders={"AgeGroup": age_options}
)
left.plotly_chart(fig_age, width="stretch")

by_tenure = (
    filtered.groupby("TenureGroup")["Exited"].mean().mul(100).reset_index()
    .rename(columns={"Exited": "Churn Rate (%)"})
)
fig_tenure = px.bar(
    by_tenure, x="TenureGroup", y="Churn Rate (%)", text_auto=".1f",
    category_orders={"TenureGroup": tenure_order}
)
right.plotly_chart(fig_tenure, width="stretch")

st.subheader("High-value customer explorer")

threshold = df["Balance"].quantile(0.75)
st.caption(f"High-value = top 25% of all customers by balance (balance of {threshold:,.0f} or more).")

status = st.radio("Show", ["All", "Churned only", "Retained only"], horizontal=True)

view = hv
if status == "Churned only":
    view = hv[hv["Exited"] == 1]
elif status == "Retained only":
    view = hv[hv["Exited"] == 0]

c1, c2, c3 = st.columns(3)
c1.metric("High-value customers", f"{len(hv):,}")
c2.metric("High-value churners", f"{int(hv['Exited'].sum()):,}")
c3.metric("Balance held by churners", f"{hv.loc[hv['Exited'] == 1, 'Balance'].sum():,.0f}")

st.dataframe(
    view[["CustomerId", "Geography", "Gender", "Age", "Balance",
          "EstimatedSalary", "NumOfProducts", "IsActiveMember", "Exited"]]
    .sort_values("Balance", ascending=False),
    width="stretch",
    hide_index=True
)

st.subheader("Segment drill-down")

dimension = st.selectbox(
    "Choose a segment type",
    ["Geography", "Gender", "AgeGroup", "CreditBand", "TenureGroup", "BalanceSegment"]
)

orders = {
    "AgeGroup": age_options,
    "CreditBand": ["Low", "Medium", "High"],
    "TenureGroup": tenure_order,
    "BalanceSegment": ["Zero-balance", "Low-balance", "High-balance"],
}
options = orders.get(dimension, sorted(filtered[dimension].unique()))
options = [o for o in options if o in filtered[dimension].values]

value = st.selectbox("Choose a group", options)

seg = filtered[filtered[dimension] == value]
rest = filtered[filtered[dimension] != value]

seg_churn = seg["Exited"].mean() * 100
total_churners = filtered["Exited"].sum()
share_of_churn = seg["Exited"].sum() / total_churners * 100 if total_churners > 0 else 0

d1, d2, d3 = st.columns(3)
d1.metric("Customers in group", f"{len(seg):,}")
d2.metric(
    "Group churn rate", f"{seg_churn:.2f}%",
    delta=f"{seg_churn - churn_rate:+.2f} pts vs current selection",
    delta_color="inverse"
)
d3.metric("Share of all churn", f"{share_of_churn:.1f}%")

profile_cols = ["Age", "Balance", "EstimatedSalary", "CreditScore", "NumOfProducts", "Tenure"]
comparison = pd.DataFrame({
    "This group": seg[profile_cols].mean(),
    "All other customers": rest[profile_cols].mean(),
}).round(1)

st.write("Average profile: this group vs everyone else")
st.dataframe(comparison, width="stretch")

st.subheader("Churn heatmap: country × age group")

heat = pd.pivot_table(
    filtered, values="Exited", index="Geography", columns="AgeGroup", aggfunc="mean"
) * 100
heat = heat.reindex(columns=[a for a in age_options if a in heat.columns])

fig_heat = px.imshow(
    heat, text_auto=".1f", color_continuous_scale="Reds",
    aspect="auto", labels={"color": "Churn Rate (%)"}
)
st.plotly_chart(fig_heat, width="stretch")

st.subheader("Geographic Risk Index")

geo = filtered.groupby("Geography").agg(
    customers=("Exited", "count"),
    churners=("Exited", "sum"),
    churn_rate=("Exited", "mean"),
)
geo["churn_rate"] = geo["churn_rate"] * 100
geo["share_of_customers"] = geo["customers"] / geo["customers"].sum() * 100
geo["share_of_churn"] = (
    geo["churners"] / geo["churners"].sum() * 100 if geo["churners"].sum() > 0 else 0
)
geo["risk_index"] = geo["share_of_churn"] / geo["share_of_customers"]

st.dataframe(geo.round(2), width="stretch")
st.caption("Risk index = share of churn ÷ share of customers. Above 1 means the country loses more than its fair share of customers.")

st.subheader("Engagement Drop Indicator")

eng = filtered.groupby("IsActiveMember")["Exited"].mean() * 100
active = eng.get(1)
inactive = eng.get(0)

e1, e2, e3 = st.columns(3)
if active is not None:
    e1.metric("Active members churn rate", f"{active:.2f}%")
if inactive is not None:
    e2.metric("Inactive members churn rate", f"{inactive:.2f}%")
if active and inactive:
    e3.metric("Engagement Drop Indicator", f"{inactive / active:.2f}x")
st.caption("Indicator = churn rate of inactive members ÷ churn rate of active members.")