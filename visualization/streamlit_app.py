# streamlit_app.py
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime

from core.core import AdministrativeHistory
from utils.helper_functions import load_config

from visualization.adm_unit_plots import plot_district_existence, plot_territorial_state_info

st.set_page_config(page_title="District Timeline Viewer", layout="wide")
st.title("District Existence Timelines")

# Load data
@st.cache_resource
def load_history():
    config = load_config("config.json")
    return AdministrativeHistory(config)

administrative_history = load_history()

# Sidebar for user to choose which plot to view
plot_type = st.sidebar.selectbox("Choose Plot Type", ["District Existence Plot", "Territorial State Information Plot"])

# Function to select the appropriate plot based on sidebar choice
def plot_based_on_selection(plot_type, administrative_history: AdministrativeHistory):
    if plot_type == "District Existence Plot":
        start_date = administrative_history.timespan.start
        end_date = administrative_history.timespan.end
        dist_registry = administrative_history.dist_registry
        return plot_district_existence(dist_registry, start_date, end_date)
    elif plot_type == "Territorial State Information Plot":
        start_date = administrative_history.timespan.start
        end_date = administrative_history.timespan.end
        dist_registry = administrative_history.dist_registry
        return plot_territorial_state_info(dist_registry, start_date, end_date)
    else:
        st.warning("Unsupported plot type selected.")
        return go.Figure()

# Generate the plot based on user selection
fig = plot_based_on_selection(plot_type, administrative_history)

# Show in Streamlit
st.plotly_chart(fig, use_container_width=True)