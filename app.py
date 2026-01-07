import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# ---------------------------------
# PAGE CONFIG
# ---------------------------------
st.set_page_config(
    page_title="ETABS Reaction Heatmap",
    layout="wide"
)

st.title("ETABS Reaction Heatmap (Streamlit)")
st.markdown("""
This app allows you to inspect results from an uploaded ETABS output file.

**Required Excel sheets:**
- Joint Reactions
- Objects and Elements - Joints

**Optional Excel sheet (for footing visualization):**
- Footing Sizes

**Units expected:**
- Loads: **kN**
- Coordinates: **mm**
- Footing sizes: **mm**
""")

# ---------------------------------
# PROCESS ETABS FILE
# ---------------------------------
def process_etabs_file(uploaded_file):
    xls = pd.ExcelFile(uploaded_file)
    available_sheets = xls.sheet_names

    # Joint reactions
    loads_df = pd.read_excel(
        uploaded_file,
        sheet_name="Joint Reactions",
        skiprows=1
    ).dropna(subset=["Unique Name", "Output Case"])

    # Joint coordinates
    coords_df = pd.read_excel(
        uploaded_file,
        sheet_name="Objects and Elements - Joints",
        skiprows=1
    ).dropna(subset=["Object Name", "Global X", "Global Y"])

    coords_df = coords_df.rename(columns={
        "Object Name": "Unique Name"
    })

    merged_df = loads_df.merge(coords_df, on="Unique Name", how="inner")

    # Optional footing sizes
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

# ---------------------------------
# FILE UPLOAD
# ---------------------------------
uploaded_file = st.file_uploader(
    "Upload ETABS exported .xlsx",
    type=["xlsx"]
)

if uploaded_file:
    try:
        load_combos, merged_df, footing_available = process_etabs_file(uploaded_file)

        # ---------------------------------
        # LOAD COMBINATION SELECTION
        # ---------------------------------
        selected_load_combo = st.selectbox(
            "Select available load combinations",
            load_combos
        )

        if selected_load_combo:
            filtered_df = merged_df[
                merged_df["Output Case"] == selected_load_combo
            ]

            if not footing_available:
                st.warning(
                    "⚠ 'Footing Sizes' sheet not found. "
                    "Showing joint reactions only."
                )

            # ---------------------------------
            # PLOTTING
            # ---------------------------------
            fig = go.Figure()

            for _, row in filtered_df.iterrows():
                x = row["Global X"]
                y = row["Global Y"]
                fz = row["FZ"]

                L = row.get("Footing_L_mm")
                B = row.get("Footing_B_mm")

                # Footing rectangle
                if footing_available and pd.notna(L) and pd.notna(B):
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

                # Joint marker fallback
                else:
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

            # ---------------------------------
            # LAYOUT & AXES
            # ---------------------------------
            fig.update_layout(
                title=f"Heatmap for Output Case: {selected_load_combo}",
                xaxis_title="X (m)",
                yaxis_title="Y (m)",
                plot_bgcolor="rgba(0,0,0,0)",
                yaxis=dict(scaleanchor="x", scaleratio=1)
            )

            # mm → m axis display
            fig.update_xaxes(
                ticktext=[f"{x/1000:.3f}" for x in filtered_df["Global X"]],
                tickvals=filtered_df["Global X"]
            )

            fig.update_yaxes(
                ticktext=[f"{y/1000:.3f}" for y in filtered_df["Global Y"]],
                tickvals=filtered_df["Global Y"]
            )

            st.plotly_chart(fig, use_container_width=True)

            # ---------------------------------
            # DATA PREVIEW
            # ---------------------------------
            with st.expander("Show processed data"):
                st.dataframe(filtered_df)

    except Exception as e:
        st.error(f"Error processing file: {e}")

else:
    st.info("Please upload an ETABS exported Excel file to begin.")
