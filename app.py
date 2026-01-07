import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# -------------------------------------------------
# PAGE SETUP
# -------------------------------------------------
st.set_page_config(
    page_title="ETABS Footing Reaction Heatmapsss",
    layout="wide"
)

st.title("ETABS Footing Reaction Heatmap")
st.markdown("""
This app visualizes **footing reactions with actual footing size (L × B)**  
similar to ETABS / VIKTOR output.

**Units assumed**
- Coordinates: **mm**
- Reactions: **kN**
""")

# -------------------------------------------------
# FILE UPLOAD
# -------------------------------------------------
uploaded_file = st.file_uploader(
    "Upload ETABS exported .xlsx",
    type=["xlsx"]
)

# -------------------------------------------------
# HELPER: VALIDATE REQUIRED COLUMNS
# -------------------------------------------------
def validate_columns(df, required_cols, sheet_label):
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        raise ValueError(
            f"Wrong sheet selected for **{sheet_label}**.\n\n"
            f"Missing columns: {missing}\n\n"
            f"Please select the correct ETABS sheet."
        )

# -------------------------------------------------
# PROCESS FUNCTION
# -------------------------------------------------
def process_etabs_file(
    uploaded_file,
    joint_reaction_sheet,
    joint_coord_sheet,
    area_sheet
):
    dfs = pd.read_excel(
        uploaded_file,
        sheet_name=[
            joint_reaction_sheet,
            joint_coord_sheet,
            area_sheet
        ],
        skiprows=1
    )

    # ---------------- Joint Reactions ----------------
    loads_raw = dfs[joint_reaction_sheet]
    validate_columns(
        loads_raw,
        ["Unique Name", "Output Case", "FZ"],
        "Joint Reactions"
    )

    loads_df = loads_raw.dropna(
        subset=["Unique Name", "Output Case", "FZ"]
    ).copy()

    # ---------------- Joint Coordinates ----------------
    joints_raw = dfs[joint_coord_sheet]
    validate_columns(
        joints_raw,
        ["Object Name", "Global X", "Global Y"],
        "Joint Coordinates"
    )

    joints_df = joints_raw.dropna(
        subset=["Object Name", "Global X", "Global Y"]
    ).copy()

    joints_df = joints_df.rename(
        columns={"Object Name": "Joint"}
    )

    # ---------------- Footing / Area Geometry ----------------
    areas_raw = dfs[area_sheet]
    validate_columns(
        areas_raw,
        ["Object Name", "Joint", "Global X", "Global Y"],
        "Footing / Area"
    )

    areas_df = areas_raw.dropna(
        subset=["Object Name", "Joint", "Global X", "Global Y"]
    ).copy()

    # Compute footing rectangle from corner joints
    footing_geom = (
        areas_df
        .groupby("Object Name")
        .agg(
            Xmin=("Global X", "min"),
            Xmax=("Global X", "max"),
            Ymin=("Global Y", "min"),
            Ymax=("Global Y", "max")
        )
        .reset_index()
        .rename(columns={"Object Name": "Footing"})
    )

    # Center & size
    footing_geom["Xc"] = (footing_geom["Xmin"] + footing_geom["Xmax"]) / 2
    footing_geom["Yc"] = (footing_geom["Ymin"] + footing_geom["Ymax"]) / 2
    footing_geom["L"] = (footing_geom["Xmax"] - footing_geom["Xmin"]) / 1000
    footing_geom["B"] = (footing_geom["Ymax"] - footing_geom["Ymin"]) / 1000

    # ---------------- Merge reactions with joints ----------------
    merged = pd.merge(
        loads_df,
        joints_df,
        left_on="Unique Name",
        right_on="Joint",
        how="inner"
    )

    # Map each joint to nearest footing
    def nearest_footing(x, y):
        d = (footing_geom["Xc"] - x) ** 2 + (footing_geom["Yc"] - y) ** 2
        return footing_geom.loc[d.idxmin()]

    footing_rows = merged.apply(
        lambda r: nearest_footing(r["Global X"], r["Global Y"]),
        axis=1
    )

    final_df = pd.concat(
        [
            merged.reset_index(drop=True),
            footing_rows.reset_index(drop=True)
        ],
        axis=1
    )

    load_combos = final_df["Output Case"].unique().tolist()
    return load_combos, final_df

# -------------------------------------------------
# MAIN LOGIC
# -------------------------------------------------
if uploaded_file:

    xls = pd.ExcelFile(uploaded_file)
    available_sheets = xls.sheet_names

    st.subheader("Map ETABS Excel Sheets")

    joint_reaction_sheet = st.selectbox(
        "Joint Reactions sheet (contains FZ)",
        available_sheets
    )

    joint_coord_sheet = st.selectbox(
        "Joint Coordinates sheet (Global X, Y)",
        available_sheets
    )

    area_sheet = st.selectbox(
        "Footing / Area sheet (corner joints of footing)",
        available_sheets
    )

    st.info("""
**Tip for clients**
- Joint Reactions → usually named *Joint Reactions*
- Joint Coordinates → *Objects and Elements – Joints*
- Footings → *Objects and Elements – Areas*

Do **not** select *Analysis Messages*.
""")

    try:
        load_combos, data = process_etabs_file(
            uploaded_file,
            joint_reaction_sheet,
            joint_coord_sheet,
            area_sheet
        )

        selected_combo = st.selectbox(
            "Select Load Combination",
            load_combos
        )

        df = data[data["Output Case"] == selected_combo]

        # -------------------------------------------------
        # PLOT
        # -------------------------------------------------
        fig = go.Figure()

        # Draw footing rectangles
        for _, r in df.iterrows():
            fig.add_shape(
                type="rect",
                x0=r["Xmin"],
                x1=r["Xmax"],
                y0=r["Ymin"],
                y1=r["Ymax"],
                fillcolor="lightgrey",
                line=dict(color="black", width=1),
                opacity=0.8
            )

        # Text at footing center
        fig.add_trace(
            go.Scatter(
                x=df["Xc"],
                y=df["Yc"],
                mode="text",
                text=[
                    f"{r['FZ']:.1f} kN<br>{r['L']:.2f} × {r['B']:.2f} m"
                    for _, r in df.iterrows()
                ],
                textposition="middle center"
            )
        )

        fig.update_layout(
            title=f"Footing Reactions – {selected_combo}",
            xaxis_title="Global X (mm)",
            yaxis_title="Global Y (mm)",
            plot_bgcolor="white",
            xaxis=dict(scaleanchor="y", scaleratio=1)
        )

        st.plotly_chart(fig, use_container_width=True)

        # -------------------------------------------------
        # TABLE
        # -------------------------------------------------
        with st.expander("Show Footing Data Table"):
            st.dataframe(
                df[
                    [
                        "Footing",
                        "L",
                        "B",
                        "FZ",
                        "Output Case"
                    ]
                ]
            )

    except Exception as e:
        st.error(str(e))

else:
    st.info("Upload an ETABS Excel file to begin.")
