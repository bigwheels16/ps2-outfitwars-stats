from dash import Dash, html, dcc, dash_table, Output, Input
import plotly.express as px
import pandas as pd
from service import Service
import util
import components
import dash_ui as dui


external_stylesheets = [
    {
        "href": "https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css",
        "rel": "stylesheet",
        "integrity": "sha384-1BmE4kWBq78iYhFldvKuhfTAU6auU8tT94WrHftjDbrCEXSU1oBoqyl2QvZ6jIW3",
        "crossorigin": "anonymous"
    },
]

meta_tags = [
    {
        "name": "viewport",
        "content": "width=device-width, initial-scale=1"
    }
]


app = Dash(__name__, title="PS2 Outfit Wars Stats", server=True, assets_folder="../assets", external_stylesheets=external_stylesheets)

service = Service()
events = service.get_kill_events(1660173742)
df2 = pd.DataFrame(events, dtype=str)

div = html.Div(children=[
    html.H1(children="PS2 Outfit Wars Stats"),

    html.Div(id="output"),

    # dash_table.DataTable(data=df2.to_dict("records"), columns=[{"name": i, "id": i} for i in df2.columns])
])

grid = dui.Grid(_id=f"grid", num_rows=2, num_cols=1, grid_padding=5)
grid.add_element(col=1, row=1, width=1, height=1, element=div)

controlpanel = dui.ControlPanel(_id=f"controlpanel")
controlpanel.create_group(
    group="Options",
    group_title="Options"
)

world_dropdown = components.create_dropdown(f"world", "World", util.format_for_dropdown("name", "world_id", service.get_world_list()), "1", multi=False)
version_dropdown = components.create_dropdown(f"match", "Match", list(), "", multi=False)
controlpanel.add_element(world_dropdown, "Options")
controlpanel.add_element(version_dropdown, "Options")

app.layout = dui.Layout(
    grid=grid,
    controlpanel=controlpanel
)


@app.callback(
    Output(f"match_dropdown", "options"),
    Input(f"world_dropdown", "value"),
)
def update_match_list(world_id):
    return list(map(lambda x: {"label": f"{x['zone_id'] >> 16} [{x['zone_id']}]", "value": x["zone_id"]}, service.get_match_list(world_id)))


@app.callback(
    Output(f"output", "children"),
    Input(f"match_dropdown", "value"),
)
def update_vehicle_kills(zone_id):
    if zone_id:
        vehicles_killed_list = service.get_vehicle_kills(zone_id)

        vehicles_lost = []
        amount = []
        outfit = []
        for row in vehicles_killed_list:
            amount.append(row["num"])
            vehicles_lost.append(f"{row['vehicle_name']} [{row['defender_outfit']}]")
            outfit.append(row['attacker_outfit'])

        # assume you have a "long-form" data frame
        # see https://plotly.com/python/px-arguments/ for more options
        df = pd.DataFrame({
            "Vehicles Lost": vehicles_lost,
            "Kills": amount,
            "Attacker Outfit": outfit
        })
    else:
        df = pd.DataFrame({
            "Vehicles Lost": [],
            "Kills": [],
            "Attacker Outfit": []
        })

    fig = px.bar(df, x="Kills", y="Vehicles Lost", color="Attacker Outfit", barmode="relative", height=800)
    config = dict({"autosizable": True, "sendData": True, "displayModeBar": True, "modeBarButtonsToRemove": ['zoom', 'pan']})
    graph = dcc.Graph(
        id="vehicles_lost_graph",
        figure=fig,
        config=config
    )
    return [graph]


if __name__ == '__main__':
    # https://dash.plotly.com/devtools
    # `app.run_server(host='127.0.0.1', port='7080', proxy=None, debug=False, dev_tools_ui=None, dev_tools_props_check=None, dev_tools_serve_dev_bundles=None, dev_tools_hot_reload=None, dev_tools_hot_reload_interval=None, dev_tools_hot_reload_watch_interval=None, dev_tools_hot_reload_max_retry=None, dev_tools_silence_routes_logging=None, dev_tools_prune_errors=None, **flask_run_options)`
    app.run_server(host="0.0.0.0", port="8080", debug=True)
