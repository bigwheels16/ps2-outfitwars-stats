from dash import Dash, html, dcc, dash_table, Output, Input
import plotly.express as px
import pandas as pd
from service import Service
import util
import components
import dash_ui as dui
import config
from db import DB
from collections import Counter
from urllib.parse import parse_qs


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
           external_stylesheets=external_stylesheets,
           url_base_pathname="/")

db = DB()
db.connect(
    config.DB_DRIVERNAME(),
    config.DB_USERNAME(),
    config.DB_PASSWORD(),
    config.DB_NAME(),
    config.DB_HOST(),
    config.DB_IP_TYPE())


service = Service(db)

div = html.Div(children=[
    html.H1(children="PS2 Outfit Wars Stats"),

    html.Div(id="outfit_stats"),

    html.Div(id="vehicle_kills"),

    html.Div(id="infantry_stats"),

    html.Div(id="infantry_kills"),

    html.Div(id="vehicle_deaths"),

    dcc.Location(id="url", refresh=False),

    dcc.Location(id="url2", refresh=False),
])

grid = dui.Grid(_id=f"grid", num_rows=2, num_cols=1, grid_padding=5)
grid.add_element(col=1, row=1, width=1, height=1, element=div)

controlpanel = dui.ControlPanel(_id=f"controlpanel")
controlpanel.create_group(
    group="Options",
    group_title="Options"
)

world_dropdown = components.create_dropdown(f"world", "World", util.format_for_dropdown("name", "world_id", service.get_world_list()), "1", multi=False)
match_dropdown = components.create_dropdown(f"match", "Match", list(), None, multi=False)
character_dropdown = components.create_dropdown(f"character", "Character", list(), [], multi=True)
controlpanel.add_element(world_dropdown, "Options")
controlpanel.add_element(match_dropdown, "Options")
controlpanel.add_element(character_dropdown, "Options")

app.layout = dui.Layout(
    grid=grid,
    controlpanel=controlpanel
)


# https://colorkit.co/color-shades-generator
# https://mdigi.tools/color-shades/
colors = [
    ["#1e487b", "#3278cd", "#84aee1"],
    ["#961c03", "#fb2f04", "#fc8269"],
    ["#61911f", "#85c42d", "#91ca4c"],
    ["#5a226b", "#a33ec1", "#cc94dd"],
]


def get_attacker(r):
    if r['attacker_outfit'] is None:
        return "Unknown"

    category = "Opponent"
    if r['is_suicide'] == 1:
        category = "Self Kill"
    elif r['attacker_outfit'] == r['defender_outfit']:
        category = "Team Kill"

    return "[%s] %s" % (r['attacker_outfit'], category)


@app.callback(
    Output(f"match_dropdown", "options"),
    Input(f"world_dropdown", "value"),
)
def update_match_list(world_id):
    if not world_id:
        return []

    return list(map(lambda x: {"label": x["zone_id"], "value": x["zone_id"]}, service.get_match_list(world_id)))


@app.callback(
    Output(f"character_dropdown", "options"),
    Input(f"world_dropdown", "value"),
    Input(f"match_dropdown", "value"),
)
def update_character_list(world_id, zone_id):
    if not world_id or not zone_id:
        return []

    return list(map(lambda x: {"label": "[%s] %s" % (x["outfit"], x["name"]), "value": f"{x['character_id']}"}, service.get_character_list(world_id, zone_id)))


@app.callback(
    Output(f"outfit_stats", "children"),
    Input(f"world_dropdown", "value"),
    Input(f"match_dropdown", "value"),
    Input(f"character_dropdown", "value"),
)
def update_outfit_stats(world_id, zone_id, character_ids):
    if not world_id or not zone_id:
        return []

    rows = service.get_outfit_stats(world_id, zone_id, character_ids)
    events = []
    for row in rows:
        d = { k: v for k, v in row.items() }

        events.append(d)

    df2 = pd.DataFrame(events)

    return [
        html.H1("Outfit Stats"),
        dash_table.DataTable(data=df2.to_dict("records"),
                             columns=[{"name": i, "id": i} for i in df2.columns],
                             page_size=5,
                             sort_action="native",
                             sort_by=[{"column_id": "num_players", "direction": "desc"}],
                             page_action="native"),
        html.Br()
    ]


@app.callback(
    Output(f"vehicle_kills", "children"),
    Input(f"world_dropdown", "value"),
    Input(f"match_dropdown", "value"),
    Input(f"character_dropdown", "value"),
)
def update_vehicle_kills(world_id, zone_id, character_ids):
    if not world_id or not zone_id:
        return []

    col1 = "Vehicle [Outfit]"
    col2 = "Amount Lost"
    col3 = "Attacker"

    results = service.get_vehicle_kills(world_id, zone_id, character_ids)
    # print(vehicles_killed_list)

    col1_values = []
    col2_values = []
    col3_values = []
    outfits = Counter()
    for row in results:
        vehicle_name = "%s %s" % (row['vehicle_category'], row['vehicle_name']) if row['vehicle_category'] else row['vehicle_name']

        col2_values.append(row["num"])
        col1_values.append(f"{vehicle_name} [{row['defender_outfit']}]")
        col3_values.append(get_attacker(row))
        if row["attacker_outfit"]:
            outfits[row["attacker_outfit"]] += 1

    color_map = {}
    col3_order = []
    for j, category in enumerate(["Opponent", "Team Kill", "Self Kill"]):
        # for i, outfit in enumerate([v for k, v in sorted(d.items(), key=lambda item: item[1])]): print(i, outfit)
        for i, outfit in enumerate(dict(outfits.most_common()).keys()):
            if len(colors) > i and len(colors[i]) > j:
                outfit_category = "[%s] %s" % (outfit, category)
                color_map[outfit_category] = colors[i][j]
                col3_order.append(outfit_category)

    color_map["Unknown"] = "black"

    # assume you have a "long-form" data frame
    # see https://plotly.com/python/px-arguments/ for more options
    df = pd.DataFrame({
        col1: col1_values,
        col2: col2_values,
        col3: col3_values
    })

    fig = px.bar(df, x=col2, y=col1, color=col3, barmode="relative", height=800, title="Vehicles Lost",
                 color_discrete_map=color_map,
                 category_orders={
                     col1: sorted(set(df[col1].values)),
                     col3: col3_order
                 })

    conf = dict({"autosizable": True, "sendData": True, "displayModeBar": True, "modeBarButtonsToRemove": ['zoom', 'pan']})
    graph = dcc.Graph(
        id="vehicles_lost_graph",
        figure=fig,
        config=conf
    )

    return [
        graph,
        html.Br(),
    ]


@app.callback(
    Output(f"infantry_stats", "children"),
    Input(f"world_dropdown", "value"),
    Input(f"match_dropdown", "value"),
    Input(f"character_dropdown", "value"),
)
def update_infantry_stats(world_id, zone_id, character_ids):
    if not world_id or not zone_id:
        return []

    col1 = "Action [Outfit]"
    col2 = "Count"
    col3 = "Outfit"

    results = service.get_infantry_stats(world_id, zone_id, character_ids)

    col1_values = []
    col2_values = []
    col3_values = []
    for row in results:
        col2_values.append(row["num"])
        col1_values.append(f"{row['action']} [{row['outfit']}]")
        col3_values.append(f"[{row['outfit']}]")

    color_map = {}
    for i, outfit in enumerate(sorted(set(col3_values))):
        if len(colors) > i:
            color_map[outfit] = colors[i][0]
    color_map["Unknown"] = "black"

    # assume you have a "long-form" data frame
    # see https://plotly.com/python/px-arguments/ for more options
    df = pd.DataFrame({
        col1: col1_values,
        col2: col2_values,
        col3: col3_values
    })

    fig = px.bar(df, x=col2, y=col1, color=col3, barmode="relative", height=800, title="Infantry Stats",
                 color_discrete_map=color_map,
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

    return [
        graph,
        html.Br(),
    ]


@app.callback(
    Output(f"infantry_kills", "children"),
    Input(f"world_dropdown", "value"),
    Input(f"match_dropdown", "value"),
    Input(f"character_dropdown", "value"),
)
def update_kills_by_weapon(world_id, zone_id, character_ids):
    if not world_id or not zone_id:
        return []

    rows = service.get_kills_by_weapon(world_id, zone_id, character_ids)
    events = []
    for row in rows:
        d = { k: v for k, v in row.items() }
        d['kills'] -= d['team_kills']
        d['team_kills'] -= d['suicides']
        events.append(d)

    df2 = pd.DataFrame(events)

    return [
        html.H1("Infantry Kills By Weapon"),
        dash_table.DataTable(data=df2.to_dict("records"),
                             columns=[{"name": i, "id": i} for i in df2.columns],
                             page_size=20,
                             sort_action="native",
                             sort_by=[{"column_id": "kills", "direction": "desc"}],
                             page_action="native"),
        html.Br(),
    ]


@app.callback(
    Output(f"vehicle_deaths", "children"),
    Input(f"world_dropdown", "value"),
    Input(f"match_dropdown", "value"),
    Input(f"character_dropdown", "value"),
)
def update_vehicle_deaths_by_weapon(world_id, zone_id, character_ids):
    if not world_id or not zone_id:
        return []

    rows = service.get_vehicle_deaths_by_weapon(world_id, zone_id, character_ids)
    events = []
    for row in rows:
        d = { k: v for k, v in row.items() }
        d['deaths'] -= d['team_deaths']
        d['team_deaths'] -= d['suicides']
        events.append(d)

    df2 = pd.DataFrame(events)

    return [
        html.H1("Vehicle Deaths By Weapon"),
        dash_table.DataTable(data=df2.to_dict("records"),
                             columns=[{"name": i, "id": i} for i in df2.columns],
                             page_size=20,
                             sort_action="native",
                             sort_by=[{"column_id": "deaths", "direction": "desc"}],
                             page_action="native")
    ]

@app.callback(
    Output(f"world_dropdown", "value"),
    Output(f"match_dropdown", "value"),
    Output(f"character_dropdown", "value"),
    Input("url2", "search"),
)
def update_params(query_string):
    params = parse_qs(query_string[1:])

    character_ids = params.get("character_ids")
    if character_ids:
        character_ids = character_ids[0].split(",")

    return (
        params.get("world_id", ["1"])[0],
        params.get("match_id", [None])[0],
        character_ids,
    )

@app.callback(
    Output("url", "search"),
    Input(f"world_dropdown", "value"),
    Input(f"match_dropdown", "value"),
    Input(f"character_dropdown", "value"),
)
def update_url(world_id, match_id, character_ids):
    params = []
    if world_id:
        params.append(f"world_id={world_id}")
    if match_id:
        params.append(f"match_id={match_id}")
    if character_ids:
        params.append(f"character_ids={','.join(character_ids)}")

    return "?" + "&".join(params)