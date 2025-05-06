import pandas as pd
import json
import os
from datetime import datetime
import matplotlib.pyplot as plt
from matplotlib.image import imread
from io import BytesIO
import base64
import io

def load_and_clean_csv(file_path, district_registry):
    # Read the CSV
    df = pd.read_csv(file_path)

    if {'region', 'district'}.issubset(df.columns):
        df['region'] = df['region'].str.upper()
        df['district'] = df['district'].str.upper()

    r_d_aim_new = []
    d_not_in_registry = []

    for idx, dist_aim in df['district'].items():
        dist_name = district_registry.find_district(dist_aim)
        if dist_name is None:
            d_not_in_registry.append(dist_aim)
        elif dist_name != dist_aim:
            print(f"Warning: name {dist_aim} is an alternative district name. Processing further as {dist_name}")

        df.at[idx, 'district'] = dist_name

    if d_not_in_registry:
            raise ValueError(f"District names {d_not_in_registry} do not exist in the district registry.")

    return df

def load_config(config_path="config.json"):
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Configuration file {config_path} not found.")
    
    with open(config_path, "r") as config_file:
        config_data = json.load(config_file)
    
    # Convert global_timespan start and end dates to datetime objects
    global_timespan = config_data.get("global_timespan", {})
    if "start" in global_timespan:
        global_timespan["start"] = datetime.strptime(global_timespan["start"], "%Y-%m-%d")
    if "end" in global_timespan:
        global_timespan["end"] = datetime.strptime(global_timespan["end"], "%Y-%m-%d")
    
    return config_data

def build_plot_from_layers(*layers):
    fig, ax = plt.subplots(figsize=(10, 10))
    for layer in layers:
        # For debugging, uncomment:
        # print(layer.to_string())

        # Group and plot by shared plotting attributes to decrease computation time
        group_cols = ["color", "edgecolor", "linewidth"]
        grouped = layer.groupby(group_cols)
        for (color, edgecolor, linewidth), group in grouped:
            group.plot(
                ax=ax,
                color=color,
                edgecolor=edgecolor,
                linewidth=linewidth
            )
    ax.set_axis_off()
    return fig

def combine_figures(fig1, fig2):
    # Save both figures to image buffers
    buf1 = BytesIO()
    buf2 = BytesIO()
    fig1.savefig(buf1, format='png', bbox_inches='tight')
    fig2.savefig(buf2, format='png', bbox_inches='tight')
    buf1.seek(0)
    buf2.seek(0)

    # Read them back as images
    img1 = imread(buf1)
    img2 = imread(buf2)

    # Create a new figure with two subplots
    fig, axes = plt.subplots(1, 2, figsize=(20, 10))
    axes[0].imshow(img1)
    axes[1].imshow(img2)

    # Hide axes
    for ax in axes:
        ax.axis('off')

    plt.tight_layout()
    return fig

def save_plot_to_html(fig, html_path, title, description, append=False):
    buffer = io.BytesIO()
    fig.savefig(buffer, format="png", bbox_inches="tight")
    buffer.seek(0)
    img_base64 = base64.b64encode(buffer.read()).decode("utf-8")
    plt.close(fig)

    html_content = f"""
    <div style="text-align:center; font-family:sans-serif; margin-top:2em;">
        <h2>{title}</h2>
        <p>{description}</p>
        <img src="data:image/png;base64,{img_base64}" />
    </div>
    """

    write_mode = "a" if append and os.path.exists(html_path) else "w"
    with open(html_path, write_mode, encoding="utf-8") as f:
        f.write(html_content)

    print(f"Plot {'appended to' if append else 'saved to'} {html_path}")
