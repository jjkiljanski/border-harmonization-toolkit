import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

def plot_district_existence(dist_registry, start_date, end_date):

    districts = dist_registry.unit_list
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

    return fig
    
def plot_territorial_state_info(dist_registry, start_date, end_date):
    districts = dist_registry.unit_list
    districts.sort(key=lambda d: d.name_id)

    # Flatten states into a dataframe
    timeline_data = []
    for district in districts:
        for state in district.states:
            has_territory = state.current_territory is not None
            timeline_data.append({
                "StateInfo": f"{district.name_id} {str(state.timespan)}",
                "Start": state.timespan.start,
                "Finish": state.timespan.end,
                "District": district.name_id,
                "Color": "#2ca02c" if has_territory else "#a9a9a9"  # Assign color based on the territory information
            })

    df = pd.DataFrame(timeline_data)

    # Create timeline plot with green/grey bars based on Territory presence
    fig = px.timeline(
        df,
        x_start="Start",
        x_end="Finish",
        y="District",
        color_discrete_sequence=["#a9a9a9"],  # Default grey, will override per trace
        hover_name="StateInfo",
        title="Territorial State Information"
    )

    # Apply per-bar color from the "Color" column
    fig.update_traces(marker=dict(color=df["Color"]))

    # Add vertical dotted lines and year labels
    for year in range(start_date.year, end_date.year + 1):
        fig.add_shape(
            type="line",
            xref="x", yref="paper",
            x0=datetime(year, 1, 1), x1=datetime(year, 1, 1),
            y0=0, y1=1,
            line=dict(color="black", width=1, dash="dot")
        )
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

    fig.update_layout(
        height=max(500, 45 * len(df['District'].unique())),
        xaxis_range=[start_date, end_date],
        showlegend=False,
    )

    fig.update_yaxes(autorange="reversed")
    fig.update_traces(width=0.6)

    return fig