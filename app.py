import dash
from dash import dcc, html
from dash import dash_table
from dash.dependencies import Input, Output
import geopandas as gpd
import plotly.express as px
import json
import pandas as pd
import requests
import io

# --- 1. FIELD ALIAS DICTIONARY ---
field_alias = {
    "K_Miskin": "Keparahan Kemiskinan",
    "Indeks_Fis": "Indeks Kapasitas Fiskal",
    "APM_SD__7_": "APM SD",
    "Ats__DO__D": "ATS DO SD",
    "APM_SLTP__": "APM SLTP",
    "Ats__DO__1": "ATS DO SLTP",
    "APM_SLTA__": "APM SLTA",
    "Ats__DO_At": "ATS DO SLTA",
    "Ind_Pendid": "Ind Pendidikan APM",
    "Indeks_Pen": "Indeks Pendidikan DO",
    "Indeks_P_1": "Indeks Pendidikan",
    "Indeks_Kem": "Indeks Kemiskinan",
    "Indeks_Kap": "Indeks Kapasitas Keuangan Daerah",
    "Indeks_Tot": "Indeks Total Pendidikan",
    "Ranking": "Ranking"
}

# --- 1. LOAD DATA GEOJSON DARI GOOGLE DRIVE ---
# Ganti dengan ID file kamu sendiri!
url = "https://drive.google.com/file/d/15o23_u56048edFmDE-6vaomGJiT9SB3a/view?usp=sharing"

response = requests.get(url)
gdf = gpd.read_file(io.BytesIO(response.content))

gdf["id"] = gdf.index.astype(str)
gdf['geometry'] = gdf['geometry'].simplify(0.01)  # jika ingin lebih ringan, bisa naikkan jadi 0.05
geojson = json.loads(gdf.to_json())


numeric_cols = [col for col in field_alias.keys() if col in gdf.columns and pd.api.types.is_numeric_dtype(gdf[col])]
default_field = numeric_cols[0] if numeric_cols else None

fields_needed = ["Kab_Kota", "Provinsi_1"] + numeric_cols
gdf = gdf[fields_needed + ["id", "geometry"]]

app = dash.Dash(__name__)
app.title = "Peta Prioritas Pembangunan Sekolah Rakyat"

app.layout = html.Div([
    html.H1("Peta Prioritas Pembangunan Sekolah Rakyat", style={"textAlign": "center"}),
    html.Div([
        html.Label("Pilih atribut prioritas:", style={"fontWeight": "bold"}),
        dcc.Dropdown(
            id='dropdown-field',
            options=[{'label': field_alias.get(col, col), 'value': col} for col in numeric_cols],
            value=default_field,
            clearable=False,
            style={"width": "340px"}
        )
    ], style={"padding": "20px", "maxWidth": "400px", "margin": "auto"}),

    dcc.Graph(id="map", config={"displayModeBar": False}),

    html.H3("Tabel Data Wilayah", style={"textAlign": "left", "marginLeft": "40px"}),
    dcc.Input(
        id='search-box', type='text', placeholder='Cari Kabupaten/Kota…', debounce=True,
        style={"width": "300px", "marginLeft": "40px", "marginBottom": "10px"}
    ),
    html.Div(
        id="data-table",
        style={"display": "flex", "justifyContent": "center", "paddingBottom": "60px"}
    )
])

@app.callback(
    Output("map", "figure"),
    Input("dropdown-field", "value")
)
def update_map(selected_field):
    alias = field_alias.get(selected_field, selected_field)
    fig = px.choropleth(
        gdf, geojson=geojson, locations="id",
        color=selected_field,
        hover_name="Kab_Kota",
        featureidkey="properties.id",
        color_continuous_scale="YlOrRd",
        labels={selected_field: alias}
    )
    # Atur center Indonesia dan tingkat zoom
    fig.update_geos(
        fitbounds="locations",
        visible=False,
        projection_scale=6.5,  # nilai antara 5–7 biasanya cocok untuk Indonesia
        center=dict(lat=-2, lon=118)  # tengah Indonesia
    )
    fig.update_layout(
        margin=dict(r=0, t=0, l=0, b=0),
        coloraxis_colorbar=dict(title=alias),
        height=600,
        geo=dict(bgcolor='rgba(0,0,0,0)')
    )
    return fig

@app.callback(
    Output("data-table", "children"),
    [Input("dropdown-field", "value"),
     Input("search-box", "value")]
)
def update_table(selected_field, search):
    alias = field_alias.get(selected_field, selected_field)
    table_df = gdf[["Kab_Kota", "Provinsi_1", selected_field]].copy()
    table_df = table_df.rename(columns={
        "Kab_Kota": "Kabupaten/Kota",
        "Provinsi_1": "Provinsi",
        selected_field: alias
    })
    # Search filter
    if search:
        mask = table_df["Kabupaten/Kota"].str.contains(search, case=False, na=False)
        table_df = table_df[mask]
    return dash_table.DataTable(
        columns=[{"name": i, "id": i, "deletable": False} for i in table_df.columns],
        data=table_df.to_dict('records'),
        style_cell={
            'textAlign': 'center',
            'padding': '8px',
            'minWidth': '120px', 'width': '120px', 'maxWidth': '180px',
            'whiteSpace': 'normal'
        },
        style_header={
            'fontWeight': 'bold',
            'backgroundColor': '#f4f4f4',
            'textAlign': 'center'
        },
        style_table={'overflowX': 'auto'},
        page_size=20,
    )

    # Tampilkan hanya max 20 baris pertama
    table_df = table_df.head(20)
    return html.Table([
        html.Thead(
            html.Tr([html.Th(col) for col in table_df.columns])
        ),
        html.Tbody([
            html.Tr([
                html.Td(row[col]) if col != alias else html.Td(f"{row[alias]:.2f}" if pd.notnull(row[alias]) else "-")
                for col in table_df.columns
            ]) for _, row in table_df.iterrows()
        ])
    ], style={"width": "100%", "borderCollapse": "collapse", "fontSize": "15px"})

if __name__ == '__main__':
    app.run(debug=True)


