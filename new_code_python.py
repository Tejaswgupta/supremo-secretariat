import networkx as nx
import pandas as pd

import plotly.graph_objs as go
from dash import Dash, Input, Output, dcc, html
from dash.exceptions import PreventUpdate

# Load your data
data_path = r"search_test_v4.csv"
data = pd.read_csv(data_path)

# Data Cleaning
# 1. Remove duplicates
data = data.drop_duplicates()

# 2. Handle missing values (example: fill with 'Unknown' or drop)
data = data.fillna("Unknown")

# Ensure columns are string type before using .str accessor
columns_to_strip = ["Name", "Allotment Year", "Place of Domicile", "Identity No"]
for col in columns_to_strip:
    data[col] = data[col].astype(str).str.strip()

# Convert 'Allotment Year' back to numeric for outlier detection
data["Allotment Year"] = pd.to_numeric(data["Allotment Year"], errors="coerce")

# 3. Identify and remove outliers based on 'Allotment Year'
Q1 = data["Allotment Year"].quantile(0.25)
Q3 = data["Allotment Year"].quantile(0.75)
IQR = Q3 - Q1
lower_bound = Q1 - 1.5 * IQR
upper_bound = Q3 + 1.5 * IQR

# Filter out outliers
outliers = data[
    (data["Allotment Year"] < lower_bound) | (data["Allotment Year"] > upper_bound)
]
data_cleaned = data[
    (data["Allotment Year"] >= lower_bound) & (data["Allotment Year"] <= upper_bound)
]

# Debug: Check number of outliers and cleaned data
print(f"Number of outliers detected: {len(outliers)}")
print("Cleaned data:")
print(data_cleaned.head())

# Ensure the expected columns are in the cleaned data
required_columns = ["Identity No", "Name", "Allotment Year", "Place of Domicile"]
for col in required_columns:
    if col not in data_cleaned.columns:
        raise ValueError(f"Missing required column: {col}")

# Create Dash app
app = Dash(__name__)

# Create a list of dropdown options
dropdown_options = [
    {"label": row["Name"], "value": row["Identity No"]}
    for _, row in data_cleaned.iterrows()
]

# Debug: Check dropdown options
print("Dropdown options:")
print(dropdown_options[:5])

app.layout = html.Div(
    [
        dcc.Dropdown(
            id="dropdown_name", options=dropdown_options, placeholder="Select a Name"
        ),
        html.Div(id="officer_details"),
        dcc.Graph(id="attribute_graph"),
        dcc.RadioItems(
            id="attribute_selector",
            options=[
                {"label": "Allotment Year", "value": "Allotment Year"},
                {"label": "Place of Domicile", "value": "Place of Domicile"},
            ],
            value="Allotment Year",
            labelStyle={"display": "inline-block"},
        ),
    ]
)


@app.callback(
    [Output("officer_details", "children"), Output("attribute_graph", "figure")],
    [Input("dropdown_name", "value"), Input("attribute_selector", "value")],
)
def update_graph(selected_id, selected_attribute):
    if not selected_id:
        raise PreventUpdate

    # Retrieve selected officer's data
    selected_officer = data_cleaned[data_cleaned["Identity No"] == selected_id].iloc[0]
    details = [
        html.P(f"{key}: {value}")
        for key, value in selected_officer.items()
        if key != "Name" and not pd.isna(value)
    ]

    # Create a network graph
    G = nx.Graph()
    G.add_node(selected_officer["Name"])

    # Add nodes and edges for officers with the same attribute value
    related_officers = data_cleaned[
        data_cleaned[selected_attribute] == selected_officer[selected_attribute]
    ]
    for _, officer in related_officers.iterrows():
        if officer["Identity No"] != selected_id:
            G.add_node(officer["Name"])
            G.add_edge(selected_officer["Name"], officer["Name"])

    pos = nx.spring_layout(G)
    edge_x = []
    edge_y = []

    for edge in G.edges():
        x0, y0 = pos[edge[0]]
        x1, y1 = pos[edge[1]]
        edge_x += [x0, x1, None]
        edge_y += [y0, y1, None]

    edge_trace = go.Scatter(
        x=edge_x,
        y=edge_y,
        line=dict(width=1, color="#888"),
        hoverinfo="none",
        mode="lines",
    )

    node_x = []
    node_y = []
    node_text = []
    node_color = []

    for node in G.nodes():
        x, y = pos[node]
        node_x.append(x)
        node_y.append(y)
        node_text.append(node)
        node_color.append(len(list(G.neighbors(node))))

    node_trace = go.Scatter(
        x=node_x,
        y=node_y,
        text=node_text,
        mode="markers+text",
        textposition="bottom center",
        hoverinfo="text",
        marker=dict(
            showscale=True,
            colorscale="YlGnBu",
            reversescale=True,
            color=node_color,
            size=10,
            colorbar=dict(
                thickness=15,
                title="Node Connections",
                xanchor="left",
                titleside="right",
            ),
        ),
    )

    fig = go.Figure(
        data=[edge_trace, node_trace],
        layout=go.Layout(
            title="Network graph of officers",
            titlefont_size=16,
            showlegend=False,
            hovermode="closest",
            margin=dict(b=20, l=5, r=5, t=40),
            annotations=[
                dict(
                    text="Node size represents number of connections",
                    showarrow=False,
                    xref="paper",
                    yref="paper",
                    x=0.005,
                    y=-0.002,
                )
            ],
            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        ),
    )

    return details, fig


# Run app
if __name__ == "__main__":
    app.run_server(port=8051, debug=True, host="0.0.0.0")
