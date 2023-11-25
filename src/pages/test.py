import dash


dash.register_page(__name__, name="Test", group="Test")

counter = 0

layout = dash.html.Div([dash.dcc.Dropdown(id="test"), dash.html.Div(id="dummy-none")])


@dash.callback(dash.Output("test", "options"), dash.Input("dummy-none", "children"))
def blah(_) -> list[str]:
    global counter
    counter += 1
    return [str(x) for x in range(counter)]
