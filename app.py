import streamlit as st
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(
    page_title="aaaaaaaaaaaaaaETABS Reaction Heatmap",
    layout="wide"
)

st.title("ETABS Reaction Heatmap (Streamlit)")
st.markdown("""
This app allows you to inspect results from an uploaded ETABS output file.

**Required Excel sheets:**
- Joint Reactions
- Objects and Elements - Joints

Units expected:
- Loads: **kN**
- Coordinates: **mm**
""")

# -------------------------------
# PROCESS ETABS FILE (same logic)
# -------------------------------
def process_etabs_file(uploaded_file):
    xls = pd.ExcelFile(uploaded_file)
    available_sheets = xls.sheet_names

    loads_df = pd.read_excel(
        uploaded_file,
        sheet_name="Joint Reactions",
        skiprows=1
    )

    coords_df = pd.read_excel(
        uploaded_file,
        sheet_name="Objects and Elements - Joints",
        skiprows=1
    )

    coords_df = coords_df.rename(columns={
        "Object Name": "Unique Name"
    })

    merged_df = loads_df.merge(coords_df, on="Unique Name", how="inner")

    # ✅ OPTIONAL Footing Sizes
    if "Footing Sizes" in available_sheets:
        footing_df = pd.read_excel(
            uploaded_file,
            sheet_name="Footing Sizes"
        )
        merged_df = merged_df.merge(
            footing_df,
            on="Unique Name",
            how="left"
        )
        footing_available = True
    else:
        footing_available = False
        merged_df["Footing_L_mm"] = None
        merged_df["Footing_B_mm"] = None

    load_combos = merged_df["Output Case"].unique().tolist()

    return load_combos, merged_df.reset_index(drop=True), footing_available




# -------------------------------
# FILE UPLOAD (FileField)
# -------------------------------
uploaded_file = st.file_uploader(
    "Upload ETABS exported .xlsx",
    type=["xlsx"]
)

if uploaded_file:
    try:
        load_combos, merged_df, footing_available = process_etabs_file(uploaded_file)


        # -------------------------------
        # LOAD COMBO SELECT (OptionField)
        # -------------------------------
        selected_load_combo = st.selectbox(
            "Select available load combinations",
            load_combos
        )

        if selected_load_combo:
            filtered_df = merged_df[
                merged_df["Output Case"] == selected_load_combo
            ]

            FZ_min = filtered_df["FZ"].min()
            FZ_max = filtered_df["FZ"].max()

            # -------------------------------
            # PLOTLY HEATMAP (same as VIKTOR)
            # -------------------------------
            fig = go.Figure()

for _, row in filtered_df.iterrows():
    x = row["Global X"]
    y = row["Global Y"]
    fz = row["FZ"]

    L = row.get("Footing_L_mm")
    B = row.get("Footing_B_mm")

    if footing_available and pd.notna(L) and pd.notna(B):
        # ✅ Draw footing rectangle
        fig.add_shape(
            type="rect",
            x0=x - L / 2,
            x1=x + L / 2,
            y0=y - B / 2,
            y1=y + B / 2,
            fillcolor="rgba(255,0,0,0.4)",
            line=dict(color="black", width=1)
        )

        fig.add_trace(go.Scatter(
            x=[x],
            y=[y],
            mode="text",
            text=[f"{fz:.1f} kN"],
            textposition="middle center",
            showlegend=False
        ))
    else:
        # ✅ Fallback marker
        fig.add_trace(go.Scatter(
            x=[x],
            y=[y],
            mode="markers+text",
            marker=dict(
                size=16,
                color=fz,
                colorscale="RdYlGn_r",
                showscale=True
            ),
            text=[f"{fz:.1f}"],
            textposition="top right",
            showlegend=False
        ))

