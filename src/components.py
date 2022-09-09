from dash import dcc
from dash import html
import dash_bootstrap_components as dbc


def create_dropdown(id, label, options, default_value, multi=True):
    return wrap_with_container_label(id, label, dcc.Dropdown(
                id=f"{id}_dropdown",
                options=options,
                value=default_value,
                placeholder="Choose an option",
                multi=multi
            )
        )


def create_input(id, label, input_type, default_value):
    return wrap_with_container_label(id, label, dbc.Input(
                id=f"{id}_input",
                type=input_type,
                value=default_value,
                placeholder="Enter a value",
            )
        )


def wrap_with_container_label(id, label, component):
    return html.Div([
            html.Label(label, id=f"{id}_label"),
            component
        ],
        className="container container-xxl input-with-label")
