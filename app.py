import pandas as pd
import numpy as np
import os
import plotly.graph_objects as go
from dash import Dash, html, dcc, Input, Output

# read in data
df = pd.read_csv("Runs.csv")

# ensure dates are in datetime format
df['start_date_local'] = pd.to_datetime(df['start_date_local'])

# aggregate specific runs between my run and my friend's run
my_runs = df[(df['friendNum'] == 0) & (df['type'] == 'Run')]
f2_runs = df[(df['friendNum'] == 2) & (df['type'] == 'Run')]




# define function to perform bootstrapping
def bootstrap_mean(data, n_boot=1000):
    means = []  # initialize empty array to store means
    for _ in range(n_boot):  # repeat process many times
        sample = np.random.choice(data, size = len(data), replace = True)  # randomly sample dataset with replacement
        means.append(np.mean(sample))  # compute statistic of interest and store mean in array

    return np.array(means)

    # alternatively, shorthand, using list comprehension:
    # return np.array([(np.mean(np.random.choice(data, size=len(data), replace=True))) for _ in range(n_boot)])



app = Dash(__name__)

app.layout = html.Div([

    dcc.Store(id = "store-my-runs", data = my_runs.to_dict("records")),
    dcc.Store(id = "store-f2-runs", data = f2_runs.to_dict("records")),

    html.H2("Bootstrap Resampling Demo"),

    html.Label("Number of Resamples (max 10000):"),
    dcc.Input(
        id="n-resamples", type="number", value=1000,
        min=100, max=10000, step=100
    ),

    html.Br(),
    html.Label("Confidence Level (%):"),
    dcc.Dropdown(
        id = "ci-level",
        options = [
            {"label": "90%", "value": 90},
            {"label": "95%", "value": 95},
            {"label": "99%", "value": 99}
        ],
        value = 95,
        clearable = False,
        style = {"width": "200px", "marginTop": "5px"}
    ),

    html.Button("Generate", id="bootstrap-button", style={"marginTop": "10px"}),

    html.Div(id = "stats-text", style = {"whiteSpace": "pre-line", "marginTop": "15px", "fontSize": "16px"}),

    html.Div([
        dcc.Graph(id = "bootstrap-hist-runs", style = {"width": "100%", "height": "500px"}),
        dcc.Graph(id = "bootstrap-hist-null", style = {"width": "100%", "height": "500px"})
    ])
], style = {"maxWidth": "1200px", "margin": "auto"})
@app.callback(
    [
        Output("bootstrap-hist-runs", "figure"),
        Output("bootstrap-hist-null", "figure"),
        Output("stats-text", "children")
    ],
    [
        Input("bootstrap-button", "n_clicks"),
        Input("n-resamples", "value"),
        Input("ci-level", "value"),
        Input("store-my-runs", "data"),
        Input("store-f2-runs", "data")
    ]
)
def update_bootstrap(n_clicks, n_boot, ci_level, my_data, f2_data):
    if not n_clicks:
        return go.Figure(), go.Figure(), ""

    n_boot = min(n_boot, 10000) if n_boot else 1000

    f2_df = pd.DataFrame(f2_data)
    my_df = pd.DataFrame(my_data)

    f2_speeds = f2_df['average_speed'].values
    my_speeds = my_df['average_speed'].values
    n_f2, n_my = len(f2_speeds), len(my_speeds)

    f2_means = bootstrap_mean(f2_speeds, n_boot)
    my_means = bootstrap_mean(my_speeds, n_boot)

    f2_orig = f2_speeds.mean()
    my_orig = my_speeds.mean()
    diff_orig = my_orig - f2_orig

    alpha = 100 - ci_level
    my_ci_lower, my_ci_upper = np.percentile(my_means, [alpha / 2, 100 - alpha / 2])
    f2_ci_lower, f2_ci_upper = np.percentile(f2_means, [alpha / 2, 100 - alpha / 2])



    combined = np.concatenate([f2_speeds, my_speeds])
    null_diffs = []
    for _ in range(n_boot):
        np.random.shuffle(combined)
        boot_f2 = combined[:n_f2]
        boot_my = combined[n_f2:]
        null_diffs.append(np.mean(boot_my) - np.mean(boot_f2))

    p_val_null = np.mean(np.abs(null_diffs) >= np.abs(diff_orig))
    alpha = 100 - ci_level
    null_ci_lower, null_ci_upper = np.percentile(null_diffs, [alpha / 2, 100 - alpha / 2])

    # --- Figure 1: Bootstrap means
    fig_runs = go.Figure()
    fig_runs.add_trace(go.Histogram(x = f2_means, nbinsx = 30, name = "Friend's Runs", opacity = 0.6))
    fig_runs.add_trace(go.Histogram(x = my_means, nbinsx = 30, name = "My Runs", opacity = 0.6, marker_color = "orangered"))

    fig_runs.add_vline(x = f2_orig, line = dict(color = "darkblue", dash = "dash"))
    fig_runs.add_vline(x = my_orig, line = dict(color = "darkred", dash = "dash"))

    fig_runs.add_vline(x = f2_ci_lower, line = dict(dash="dot"))
    fig_runs.add_vline(x = f2_ci_upper, line = dict(dash="dot"))

    fig_runs.add_vline(x = my_ci_lower, line = dict(color = "orangered", dash = "dot"))
    fig_runs.add_vline(x = my_ci_upper, line = dict(color = "orangered", dash = "dot"))

    fig_runs.update_layout(
        barmode = "overlay",
        title = "Bootstrap Means: My Runs vs Friend's Runs",
        xaxis_title = "Mean Average Speed",
        yaxis_title = "Count",
        height = 500,
        legend = dict(x=0.01, y=0.99)
    )




    # --- Figure 2: Null distribution
    fig_null = go.Figure()
    fig_null.add_trace \
        (go.Histogram(x = null_diffs, nbinsx = 30, name = "Null Differences", marker_color = "purple", opacity = 0.6))

    fig_null.add_vline(x = null_ci_lower, line = dict(color = "gray", dash = "dot"))
    fig_null.add_vline(x = null_ci_upper, line = dict(color = "gray", dash = "dot"))

    fig_null.update_layout(
        title = "Null Distribution (Assuming No Difference)",
        xaxis_title = "Mean Difference Under Null",
        yaxis_title = "Count",
        height = 500,
        legend = dict(x=0.01, y=0.99)
    )

    # --- Stats text
    stats = (
        f"**Bootstrap Summary**\n"
        f"- Mean (Friend): {f2_orig:.3f} m/s\n"
        f"- {ci_level}% CI (Friend): ({f2_ci_lower:.3f}, {f2_ci_upper:.3f})\n"
        f"- Mean (Mine): {my_orig:.3f} m/s\n"
        f"- {ci_level}% CI (Mine): ({my_ci_lower:.3f}, {my_ci_upper:.3f})\n"
        f"- Observed Difference: {diff_orig:.3f} m/s\n\n"
        f"**Permutation Test (No Difference)**\n"
        f"- P-value (from null distribution): {p_val_null:.4f}\n"
        f"- {ci_level}% CI (Null): ({null_ci_lower:.3f}, {null_ci_upper:.3f})"
    )


    return fig_runs, fig_null, stats

port = int(os.environ.get("PORT", 8050))

if __name__ == "__main__":
    app.run(debug=True, host = "0.0.0.0", port = port)