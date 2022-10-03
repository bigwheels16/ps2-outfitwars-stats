from dash import Dash, html, dcc, dash_table, Output, Input
import plotly.express as px
import pandas as pd
from service import Service
import util
import components
import dash_ui as dui
import config, db


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


app = Dash(__name__,
           title="PS2 Outfit Wars Stats",
           server=True,
           assets_folder="../assets",
           external_stylesheets=external_stylesheets)

db = db.DB()
db.connect_mysql(config.DB_HOST(),
                 config.DB_PORT(),
                 config.DB_USERNAME(),
                 config.DB_PASSWORD(),
                 config.DB_DATABASE())

service = Service(db)
events = service.get_kill_events(1660173742)
df2 = pd.DataFrame(events, dtype=str)

div = html.Div(children=[
    html.H1(children="PS2 Outfit Wars Stats"),

    html.Div(id="output1"),

    html.Div(id="output2"),

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
version_dropdown = components.create_dropdown(f"match", "Match", list(), "-1", multi=False)
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
    return list(map(lambda x: {"label": f"{x['match_id']}", "value": x["match_id"]}, service.get_match_list(world_id)))


@app.callback(
    Output(f"output1", "children"),
    Input(f"match_dropdown", "value"),
)
def update_vehicle_kills(match_id):
    col1 = "Vehicles Lost"
    col2 = "Kills"
    col3 = "Attacker"

    if match_id is not None:
        results = service.get_vehicle_kills(match_id)
        # print(vehicles_killed_list)

        def get_attacker(r):
            if r['is_suicide'] == 1:
                return "Suicide"
            elif r['attacker_outfit'] is None:
                return "Unknown"
            elif r['attacker_outfit'] == r['defender_outfit']:
                return "Team Kill"
            else:
                return "Opponent"

        col1_values = []
        col2_values = []
        col3_values = []
        for row in results:
            vehicle_name = "%s %s" % (row['vehicle_category'], row['vehicle_name']) if row['vehicle_category'] else row['vehicle_name']

            col2_values.append(row["num"])
            col1_values.append(f"{vehicle_name} [{row['defender_outfit']}]")
            col3_values.append(get_attacker(row))

        # assume you have a "long-form" data frame
        # see https://plotly.com/python/px-arguments/ for more options
        df = pd.DataFrame({
            col1: col1_values,
            col2: col2_values,
            col3: col3_values
        })
    else:
        df = pd.DataFrame({
            col1: [],
            col2: [],
            col3: []
        })

    fig = px.bar(df, x=col2, y=col1, color=col3, barmode="relative", height=800, title="Vehicles Lost by Team",
                 color_discrete_map={"Opponent": "red", "Team Kill": "blue", "Suicide": "orange", "Unknown": "green"},
                 category_orders={
                     col1: sorted(set(df[col1].values)),
                     col3: ["Opponent", "Team Kill", "Suicide", "Unknown"]})

    conf = dict({"autosizable": True, "sendData": True, "displayModeBar": True, "modeBarButtonsToRemove": ['zoom', 'pan']})
    graph = dcc.Graph(
        id="vehicles_lost_graph",
        figure=fig,
        config=conf
    )
    return [graph]


@app.callback(
    Output(f"output2", "children"),
    Input(f"match_dropdown", "value"),
)
def update_infantry_stats(match_id):
    col1 = "Action"
    col2 = "Count"
    col3 = "Outfit"

    if match_id is not None:
        results = service.get_infantry_stats(match_id)

        # print(vehicles_killed_list)

        col1_values = []
        col2_values = []
        col3_values = []
        for row in results:
            col2_values.append(row["num"])
            col1_values.append(f"{row['action']} [{row['outfit']}]")
            col3_values.append(row["outfit"])

        # assume you have a "long-form" data frame
        # see https://plotly.com/python/px-arguments/ for more options
        df = pd.DataFrame({
            col1: col1_values,
            col2: col2_values,
            col3: col3_values
        })
    else:
        df = pd.DataFrame({
            col1: [],
            col2: [],
            col3: []
        })

    fig = px.bar(df, x=col2, y=col1, color=col3, barmode="relative", height=800, title="Infantry Stats",
                 category_orders={
                     col1: sorted(set(df[col1].values))
                 })

    conf = dict(
        {"autosizable": True, "sendData": True, "displayModeBar": True, "modeBarButtonsToRemove": ['zoom', 'pan']})
    graph = dcc.Graph(
        id="vehicles_lost_graph",
        figure=fig,
        config=conf
    )
    return [graph]
