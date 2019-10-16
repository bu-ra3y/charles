from datetime import datetime, time
from pathlib import Path

import dash
import dash_core_components as dcc
import dash_html_components as html
import pandas as pd
from dash.dependencies import Input, Output
import plotly.graph_objs as go

folder = Path(__file__).parent.parent / "test_data"
SITES_FILE = folder / 'Monitoring_Sites.csv'
RESULTS_FILE = folder / 'Results.csv'
METHODS_FILE = folder / 'Analytical_Methods.csv'


def load_sites():
    sites = pd.read_csv(SITES_FILE)
    # sites[['Site_Name', 'Town', 'Latitude_DD', 'Longitude_DD', 'Site_Description']]
    return sites


def load_results(sites):
    r = pd.read_csv(RESULTS_FILE, low_memory=False)

    # Accepted results only
    r = r[r['QAQC_Status'].str.lower().str.contains('accepted', na=False)]

    # Just a few columns
    r = r[['Date_Collected', 'Time_Collected', 'Site_ID', 'Reporting_Result', 'Analytical_Method_ID']]

    # Fix the Collection Date
    r['Date_Collected'] = pd.to_datetime(r['Date_Collected']).dt.date

    # Fix the Time
    r['Time_Collected'] = pd.to_datetime(r['Time_Collected'], errors='coerce').dt.time
    r['Time_Collected'].fillna(time(), inplace=True)  # Fill in missing times with 00:00

    # Create a combined Datetime column
    r['datetime'] = r.apply(lambda x: pd.datetime.combine(x['Date_Collected'], x['Time_Collected']), 1)

    # Drop unused columns
    r = r.drop(['Time_Collected'], 1)

    # Results as numbers
    r['Reporting_Result'] = pd.to_numeric(r['Reporting_Result'], errors='coerce')
    r = r[r['Reporting_Result'].notnull()]  # Filter out results that are NAN

    # Join with Sites DATA to get Site Name, lat, lon
    columns = ['Site_ID', 'Date_Collected', 'datetime', 'Reporting_Result', 'Analytical_Method_ID', 'Site_Name', 'Town', 'Latitude_DD', 'Longitude_DD', ]
    r = r.merge(right=sites, how='left', on='Site_ID')[columns]

    # Join with Analytical Methods to get Parameter name
    methods = load_methods()
    columns = ['Site_ID', 'Date_Collected', 'datetime', 'Parameter', 'Reporting_Result', 'Analytical_Method_ID', 'Site_Name', 'Town', 'Latitude_DD', 'Longitude_DD', ]
    r = r.merge(right=methods, how='left', on='Analytical_Method_ID')[columns]

    # Drop results with missing DATA in one of the required columns
    r = r.dropna(subset=['Latitude_DD', 'Longitude_DD', 'Parameter', 'Reporting_Result', 'Date_Collected', 'datetime', 'Site_ID', 'Analytical_Method_ID'])

    # TODO: limit to the 37 fixed sites
    # sites[sites['Site_ID'].isin(r['Site_ID'].unique())]

    # Sort by datetime
    r.sort_values('datetime', inplace=True)

    # See what we have
    return r


def load_methods():
    m = pd.read_csv(METHODS_FILE)
    return m


def ecoli_data(data):
    ecoli = data[data['Parameter'] == 'Escherichia coli'].copy()

    # Categorize Values into Severity Levels, thresholds are 126 and 630
    levels = ['Swimming', 'Boating', 'Danger']
    ecoli['severity'] = pd.cut(ecoli['Reporting_Result'], [0, 126, 630, 100000], right=False, labels=levels)

    color_for_category = {
        'Swimming': 'green',
        'Boating' : 'yellow',
        'Danger'  : 'blue',
    }
    ecoli['colors'] = [color_for_category[c] for c in ecoli['severity']]

    return ecoli


external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']
app = dash.Dash(__name__, external_stylesheets=external_stylesheets)
application = app.server  # Entry Point for AWS Elastic Beanstalk
DATA = load_results(load_sites())


# print(DATA)
# print(DATA.columns)


def get_dates(data):
    return sorted(list(data['Date_Collected'].unique()), reverse=True)


def get_parameters():
    parameters = [p for p in DATA.Parameter.unique() if isinstance(p, str)]
    parameters = sorted(parameters)
    # print(parameters)
    return parameters


app.layout = html.Div(children=[
    html.Div([
        dcc.Dropdown(
            id='parameter',
            options=[{'label': i, 'value': i} for i in get_parameters()],
            value='Escherichia coli',
            disabled=True,
            placeholder='Choose a parameter',
            className="five columns",
        ),
        dcc.Dropdown(
            id='date',
            options=[{'label': i, 'value': i} for i in get_dates(ecoli_data(DATA))],
            value=get_dates(ecoli_data(DATA))[0],
            placeholder='Choose a date',
            className="three columns",
        ),
    ],
        className='row'
    ),
    dcc.Graph(id='map', className='row'),
    html.H1('Select a Site', id='site-name', className='row'),
    html.Div(
        dcc.Dropdown(
            id='chart-parameters',
            options=[{'label': i, 'value': i} for i in get_parameters()],
            value=get_parameters(),
            multi=True,
            placeholder='Choose parameters to chart',
            clearable=False,
            className="twelve columns",
        ),
        className='row'),
    dcc.Graph(id='chart'),
])


def site_name_from_map_click(selected_site):
    return selected_site.get('points')[0].get('text')


@app.callback(
    Output('site-name', 'children'),
    [Input('map', 'clickData')]
)
def update_site_name(map_click):
    if not map_click:
        return 'Select a site'
    else:
        return site_name_from_map_click(map_click)


@app.callback(
    Output('chart', 'figure'),
    [Input('map', 'clickData'),
     Input('date', 'value'),
     Input('chart-parameters', 'value'), ]
)
def update_chart(map_click, date_string, parameters):
    if not map_click or not parameters:
        return go.Figure(layout=chart_layout())
    else:
        name = site_name_from_map_click(map_click)
        data = DATA[DATA['Site_Name'] == name]  # Filter to the selected Site

    date = string_date_to_date(date_string)
    # print(data)
    # print(data.columns)

    date_line = go.Scatter(
        x=(date, date),
        y=(0, 20000),
        name=date_string,
        mode='lines',
        # text=data.Site_Name if not data.empty else list(),
        # hoverinfo='text',
        showlegend=False,
    )
    traces = [go.Scatter(
        x=data[data.Parameter == parameter].datetime,
        y=data[data.Parameter == parameter].Reporting_Result,
        name=parameter,
        # line_color='grey',
        # text=data.Site_Name if not data.empty else list(),
        # hoverinfo='text',
    ) for parameter in parameters]
    traces.insert(0, date_line)
    return go.Figure(data=traces, layout=chart_layout())


def chart_layout():
    return go.Layout(
        # title=name,
        yaxis=dict(
            range=[0, 20000],
        ),
        margin=dict(t=0),
    )


def string_date_to_date(date_string):
    return datetime.strptime(date_string, '%Y-%m-%d').date()


@app.callback(
    Output('map', 'figure'),
    [Input('date', 'value'),
     Input('parameter', 'value'),
     ], )
def update_map(date, parameter):
    mapbox_access_token = None

    if date:
        data = DATA[DATA['Date_Collected'] == string_date_to_date(date)]
        data = ecoli_data(data)
    else:
        data = pd.DataFrame()

    fig = go.Figure(
        go.Scattermapbox(
            lat=data.Latitude_DD if not data.empty else list(),
            lon=data.Longitude_DD if not data.empty else list(),
            mode='markers',
            marker=go.scattermapbox.Marker(
                size=14,
                color=data.colors if not data.empty else list(),
            ),
            text=data.Site_Name if not data.empty else list(),
            hoverinfo='text',
        )
    )

    fig.update_layout(
        hovermode='closest',
        title="Sites",
        margin={"r": 0, "t": 0, "l": 0, "b": 0},
        mapbox=go.layout.Mapbox(
            accesstoken=mapbox_access_token,
            style="carto-positron",
            bearing=0,
            center=go.layout.mapbox.Center(
                lat=42.3,
                lon=-71.2
            ),
            zoom=9,
        )
    )

    return fig


if __name__ == '__main__':
    app.run_server(debug=True)
