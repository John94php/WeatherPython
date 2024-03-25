import openmeteo_requests
import requests_cache
import pandas as pd
from retry_requests import retry
from geopy.geocoders import Nominatim
from datetime import datetime
import matplotlib.pyplot as plt

cache_session = requests_cache.CachedSession('.cache', expire_after=3600)
retry_session = retry(cache_session, retries=5, backoff_factor=0.2)
openmeteo = openmeteo_requests.Client(session=retry_session)
user_city = input("Enter the city:\n")
print(user_city)
geolocator = Nominatim(user_agent="my_geocoder")
geocode = geolocator.geocode(user_city)

url = "https://api.open-meteo.com/v1/forecast"
params = {
    "latitude": geocode.latitude,
    "longitude": geocode.longitude,
    "hourly": "temperature_2m",
    "current": "temperature_2m"
}
responses = openmeteo.weather_api(url, params=params)

response = responses[0]
hourly = response.Hourly()
current = response.Current()
current_temperature_2m = current.Variables(0).Value()
timestamp = current.Time()

df_current = pd.DataFrame({
    'Current time': [datetime.fromtimestamp(timestamp)],
    'Current temperature': [round(current_temperature_2m, 2)]
})
hourly_temperature_2m = hourly.Variables(0).ValuesAsNumpy()

hourly_data = {"date": pd.date_range(
    start=pd.to_datetime(hourly.Time(), unit="s", utc=True),
    end=pd.to_datetime(hourly.TimeEnd(), unit="s", utc=True),
    freq=pd.Timedelta(seconds=hourly.Interval()),
    inclusive="left"
), "temperature_2m": hourly_temperature_2m}

hourly_dataframe = pd.DataFrame(data=hourly_data)
df = pd.DataFrame(hourly_dataframe)
df['date'] = pd.to_datetime(df['date'].dt.tz_localize(None))
plt.figure(figsize=(15, 10))
plt.plot(df['date'], df['temperature_2m'], marker='o', linestyle='-')
plt.title('Temperatura na 2 metrach')
plt.xlabel('Data')
plt.ylabel('Temperatura (°C)')
plt.grid(True)
plt.xticks(rotation=45)
writer = pd.ExcelWriter('wykres_temperatury.xlsx', engine='xlsxwriter')
df.to_excel(writer, index=False, sheet_name='Temperature per hour')
df_current.to_excel(writer, index=False, sheet_name="Current temperature")
average = sum(hourly_temperature_2m) / len(hourly_temperature_2m)
max_hourly_temp = max(hourly_temperature_2m)
min_hourly_temp = min(hourly_temperature_2m)
df_average = pd.DataFrame({
    'average_hourly_temperature': [round(average, 2)],
    'max_hourly_temperature': [max_hourly_temp],
    'min_hourly_temperature': [min_hourly_temp]
})
df_average.to_excel(writer, index=False, sheet_name="Temperature per hour", startcol=3, startrow=20)

workbook = writer.book
worksheet = writer.sheets['Temperature per hour']

chart = workbook.add_chart({'type': 'line'})
chart.add_series({
    'categories': ['Temperature per hour', 1, 0, len(df), 0],
    'values': ['Temperature per hour', 1, 1, len(df), 1],
    'marker': {'type': 'circle', 'size': 7},
})
chart.set_title({'name': 'Temperatura na 2 metrach'})
chart.set_x_axis({'name': 'Data', 'date_axis': True})
chart.set_y_axis({'name': 'Temperatura (°C)'})
worksheet.insert_chart('D2', chart)

writer._save()
