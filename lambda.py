import json
import os

import pandas as pd
import requests


COLUMNS = {
    "Satellite": "Satellite",
    "startUTC": "AOS Time",
    "startAzCompass": "AOS Az",
    "maxUTC": "MOS Time",
    "maxAzCompass": "MOS Az",
    "maxEl": "MOS El",
    "endUTC": "LOS Time",
    "endAzCompass": "LOS Az",
}


SATELLITE_IDS = {
    "ISS": 25544,
    "SO-50": 27607,
    "AO-91": 43017,
    "TEVEL-3": 50988,
    "TEVEL-4": 51063,
    "TEVEL-5": 50998,
    "PO-101": 43678,
}

BASE_URL = "https://api.n2yo.com/rest/v1/satellite/radiopasses"
API_KEY = os.environ.get("API_KEY", "")


def get_satellite_passes(satellite: str, latitude: float, longitude: float, altitude: float, min_elevation: float) -> pd.DataFrame:
    """
    For a given satellite, get all passes for the next ten days.

    Parameters
    ----------
    satellite : str
        The human-legible short-hand satellite identifier, as in SATELLITE_IDS.
    api_key : str
        The API key for N2YO.

    Returns
    -------
    pd.DataFrame
        A dataframe of all satellite passes, cleaned up and with times in Pacific time.
    """

    # Format the API URL for this satellite
    norad_id = SATELLITE_IDS[satellite]
    parameters = f"{latitude}/{longitude}/{altitude}/10/{min_elevation}"
    url = f"{BASE_URL}/{norad_id}/{parameters}?apiKey={API_KEY}"

    # Query the API
    response = requests.get(url)

    # Parse out the output
    data = json.loads(response.text)
    df = pd.DataFrame(data["passes"])

    # Round max elevation to the nearest int
    df["maxEl"] = df["maxEl"].round(0).astype(int)

    # Convert all times to Pacific time
    for col in ["startUTC", "maxUTC", "endUTC"]:
        df[col] = (
            pd.to_datetime(df[col], unit="s")
            .dt.tz_localize("UTC")
            .dt.tz_convert("US/Pacific")
        )


    # Format the datetimes to a clean string
    for col in ["startUTC", "maxUTC", "endUTC"]:
        df[col] = df[col].dt.strftime("%a %H:%M")

    # Clean up the dataframe -- add the satellite name and rename columns
    df["Satellite"] = satellite
    df = df.rename(columns=COLUMNS)[COLUMNS.values()]

    return df


def prettify_results(df: pd.DataFrame) -> str:

    table = (
        df
        .sort_values(by=["AOS Time"])
        .to_html(index=False, classes="pure-table pure-table-horizontal")
    )
    return table


def lambda_handler(event, context):
    
    params = event["queryStringParameters"]
    
    satellites = params.get("satellites").split("_") if params.get("satellites") else ["ISS"]
    latitude = params.get("latitude") if params.get("latitude") else "47.259107"
    longitude = params.get("longitude") if params.get("longitude") else "-122.460810"
    altitude = params.get("altitude") if params.get("altitude") else "0"
    min_elevation = float(params.get("min_elevation")) if params.get("min_elevation") else 30
    
    results = []
    for satellite in satellites:
        results.append(get_satellite_passes(satellite, latitude, longitude, altitude, min_elevation))
    
    table = prettify_results(pd.concat(results))
    
    return {
        "statusCode": 200,
        "body": table
    }
