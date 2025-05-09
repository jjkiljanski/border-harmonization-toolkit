# streamlit_app.py
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime

from core.core import AdministrativeHistory
from utils.helper_functions import load_config

st.set_page_config(page_title="District Timeline Viewer", layout="wide")
st.title("District Existence Timelines")

# Load data
@st.cache_resource
def load_history():
    config = load_config("config.json")
    return AdministrativeHistory(config)

administrative_history = load_history()

start_date = administrative_history.timespan.start
end_date = administrative_history.timespan.end

districts = administrative_history.dist_registry.unit_list
districts.sort(key=lambda d: d.name_id)

# Flatten states into a dataframe, assigning a unique task name for each state
timeline_data = []
for district in districts:
    for i, state in enumerate(district.states):
        timeline_data.append({
            "StateInfo": f"{district.name_id} {str(state.timespan)}",
            "Start": state.timespan.start,
            "Finish": state.timespan.end,
            "District": district.name_id
        })

df = pd.DataFrame(timeline_data)

# Create thick horizontal bars using px.timeline
fig = px.timeline(
    df,
    x_start="Start",
    x_end="Finish",
    y="District",       # This maps to 'Resource' in your example
    color="District",   # Optional: use to color by district
    title="Districts Existence Over Time",
    hover_name="StateInfo"
)

# Add horizontal (vertical in time axis) lines for each year
for year in range(start_date.year, end_date.year + 1):
    # Add vertical dotted line at the start of each year
    fig.add_shape(
        type="line",
        xref="x", yref="paper",
        x0=datetime(year, 1, 1), x1=datetime(year, 1, 1),
        y0=0, y1=1,
        line=dict(color="black", width=1, dash="dot")
    )

    # Add year label just above the line
    fig.add_annotation(
        x=datetime(year, 1, 1),
        y=1.02,
        xref="x", yref="paper",
        text=str(year),
        showarrow=False,
        font=dict(size=10, color="black"),
        align="center",
        yanchor="middle",
    )

# Set appearance
fig.update_layout(
    height=max(500, 45 * len(df['District'].unique())),
    xaxis_range=[start_date, end_date],
    showlegend=False,
)

fig.update_yaxes(autorange="reversed")

fig.update_traces(width= 0.6)

# Show in Streamlit
st.plotly_chart(fig, use_container_width=True)