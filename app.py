import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import math

# -------------------------------------------------
# PAGE CONFIG
# -------------------------------------------------
st.set_page_config(
    page_title="ETABS Pad Foundation Designer",
    layout="wide"
)

st.title("ETABS Pad Foundation Designer")
st.markdown("""
This app performs **preliminary pad foundation sizing** using ETABS column reactions.

### Workflow
1. Upload ETABS exported Excel file  
2. Select load combination  
3. Enter allowable bearing capacity  
4. View pad foundation layout  

### Required Excel sheets
- **Joint Reactions**
- **Objects and Elements - Joints**

### Units
- Loads: **kN**
- Coordinates: **mm**
- Bearing Capacity: **kPa (kN/m²)**
""")

# -------------------------------------------------
# USER INPUT – BEARING CAPACITY
# -------------------------------------------------
bearing_capacity = st.number_input(
    "Allowable Bearing Capacity (kPa)",
    min_value=50,
    max_value=500,
    value=150,
    step=10
)

st.caption("Note: 1 kPa = 1 kN/m²")

# -------------------------------------------------
# PROCESS ETABS FILE
# -------------------------------------------------
def process_etabs_file(uploaded_file):
    loads_df = pd.read_excel(
        uploaded_file,
        sheet_name="Joint Reactions",
        skiprows=1
    ).dropna(subset=["Unique Name", "Output Case"])

    coords_df = pd.read_excel(
        uploaded_file,
        sheet_name="Objects and Elements - Joints",
        skiprows=1
    ).dropna(subset=["Object Name", "Global X", "Global Y"])

    coords_df = coords_df.rename(columns={
        "Object Name": "Unique Name"
    })

    merged_df = loads_df.merge(coords_df, on="Unique Name", how="inner")
    load_combos = merged_df["Output Case"].unique().tolist()

    return load_combos, merged_df.reset_index(drop=True)

# -------------------------------------------------
# FILE UPLOAD
# -------------------------------------------------
uploaded_file = st.file_uploader(
    "Upload ETABS exported .xlsx",
    type=["xlsx"]
)

if uploaded_file:
    try:
        load_combos, merged_df = process_etabs_file(uploaded_file)

        selected_load_combo = st.selectbox(
            "Select Load Combination",
            load_combos
        )

        if selected_load_combo:
            filtered_df = merged_df[
                merged_df["Output Case"] == selected_load_combo
            ]

            st.subheader("Pad Foundation Layout")

            # -------------------------------------------------
            # PLOTTING – PAD FOUNDATION DESIGN
            # -------------------------------------------------
            fig = go.Figure()

            for _, row in filtered_df.iterrows():
                x = row["Global X"]
                y = row["Global Y"]
                fz = abs(row["FZ"])  # Compression only

                # ---- DESIGN LOGIC ----
                # Required area (m²)
                area_m2 = fz / bearing_capacity

                # Square footing
                side_m = math.sqrt(area_m2)
                side_m = max(side_m, 1.0)  # minimum 1.0 m footing

                L = side_m * 1000  # mm
                B = side_m * 1000  # mm

                # Footing rectangle
                fig.add_shape(
                    type="rect",
                    x0=x - L / 2,
                    x1=x + L / 2,
                    y0=y - B / 2,
                    y1=y + B / 2,
                    fillcolor="rgba(210,210,210,0.9)",
                    line=dict(color="black", width=2)
                )

                # Size text
                fig.add_trace(go.Scatter(
                    x=[x],
                    y=[y],
                    mode="text",
                    text=[f"{side_m:.2f} m × {side_m:.2f} m"],
                    textposition="middle center",
                    showlegend=False
                ))

            # -------------------------------------------------
            # LAYOUT & AXES
            # -------------------------------------------------
            fig.update_layout(
                title=f"Pad Foundation Layout – {selected_load_combo}",
                xaxis_title="X (m)",
                yaxis_title="Y (m)",
                plot_bgcolor="rgba(245,245,245,1)",
                yaxis=dict(scaleanchor="x", scaleratio=1)
            )

            # Axis labels in meters
            fig.update_xaxes(
                ticktext=[f"{x/1000:.2f}" for x in filtered_df["Global X"]],
                tickvals=filtered_df["Global X"]
            )

            fig.update_yaxes(
                ticktext=[f"{y/1000:.2f}" for y in filtered_df["Global Y"]],
                tickvals=filtered_df["Global Y"]
            )

            st.plotly_chart(fig, use_container_width=True)

            # -------------------------------------------------
            # DATA TABLE
            # -------------------------------------------------
            with st.expander("Show Calculation Table"):
                table_df = filtered_df.copy()
                table_df["FZ (kN)"] = table_df["FZ"].abs()
                table_df["Required Area (m²)"] = table_df["FZ (kN)"] / bearing_capacity
                table_df["Footing Size (m)"] = table_df["Required Area (m²)"].apply(
                    lambda a: round(math.sqrt(a), 2)
                )
                st.dataframe(table_df)

    except Exception as e:
        st.error(f"Error processing file: {e}")

else:
    st.info("Please upload an ETABS exported Excel file to begin.")
