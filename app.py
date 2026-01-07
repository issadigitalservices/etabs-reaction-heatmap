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
    sheet_names = [
        "Joint Reactions",
        "Objects and Elements - Joints",
        "Footing Sizes"   # 👈 NEW
    ]

    dataframes = pd.read_excel(
        uploaded_file,
        sheet_name=sheet_names,
        skiprows=1
    )

    loads_df = dataframes["Joint Reactions"].dropna(
        subset=["Unique Name", "Output Case"]
    ).copy()

    coords_df = dataframes["Objects and Elements - Joints"].dropna(
        subset=["Element Name", "Object Name", "Global X", "Global Y"]
    ).copy()

    coords_df = coords_df.rename(columns={
        "Object Name": "Unique Name"
    })

    footing_df = dataframes["Footing Sizes"].copy()

    merged_df = loads_df.merge(coords_df, on="Unique Name")
    merged_df = merged_df.merge(footing_df, on="Unique Name", how="left")

    load_combos = merged_df["Output Case"].unique().tolist()

    return load_combos, merged_df.reset_index(drop=True)



# -------------------------------
# FILE UPLOAD (FileField)
# -------------------------------
uploaded_file = st.file_uploader(
    "Upload ETABS exported .xlsx",
    type=["xlsx"]
)

if uploaded_file:
    try:
        load_combos, merged_df = process_etabs_file(uploaded_file)

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
            fig = go.Figure(
                data=go.Scatter(
                    x=filtered_df["Global X"],
                    y=filtered_df["Global Y"],
                    mode="markers+text",
                    marker=dict(
                        size=16,
                        color=filtered_df["FZ"],
                        colorscale=[
                            [0, "green"],
                            [0.5, "yellow"],
                            [1, "red"]
                        ],
                        colorbar=dict(title="FZ (kN)"),
                        cmin=FZ_min,
                        cmax=FZ_max
                    ),
                    text=[f"{fz:.1f}" for fz in filtered_df["FZ"]],
                    textposition="top right"
                )
            )

            fig.update_layout(
                title=f"Heatmap for Output Case: {selected_load_combo}",
                xaxis_title="X (m)",
                yaxis_title="Y (m)",
                plot_bgcolor="rgba(0,0,0,0)"
            )

            fig.update_xaxes(
                linecolor="LightGrey",
                ticktext=[f"{x/1000:.3f}" for x in filtered_df["Global X"]],
                tickvals=filtered_df["Global X"]
            )

            fig.update_yaxes(
                linecolor="LightGrey",
                ticktext=[f"{y/1000:.3f}" for y in filtered_df["Global Y"]],
                tickvals=filtered_df["Global Y"]
            )

            st.plotly_chart(fig, use_container_width=True)

            # Optional data preview
            with st.expander("Show processed data"):
                st.dataframe(filtered_df)

    except Exception as e:
        st.error(f"Error processing file: {e}")
else:
    st.info("Please upload an ETABS exported Excel file to begin.")
