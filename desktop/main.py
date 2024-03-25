import wx
import wx.grid
import pandas as pd
import openmeteo_requests
import requests_cache
from retry_requests import retry
from geopy.geocoders import Nominatim


class MyFrame(wx.Frame):
    def __init__(self, parent, title, df):
        super(MyFrame, self).__init__(parent, title=title, size=(600, 300))
        self.panel = wx.Panel(self)
        self.vbox = wx.BoxSizer(wx.VERTICAL)
        busy_info = wx.BusyInfo("Please wait...")
        self.df = df
        del busy_info

        self.country_choices = self.df['country'].unique()
        self.country_choice_text = wx.StaticText(self.panel, label="Choose country")
        self.vbox.Add(self.country_choice_text, 0, wx.ALL | wx.EXPAND, 5)

        self.country_choice = wx.Choice(self.panel, choices=self.country_choices)
        self.country_choice.Bind(wx.EVT_CHOICE, self.on_country_selected)
        self.vbox.Add(self.country_choice, 0, wx.ALL | wx.EXPAND, 5)

        self.city_choice = wx.Choice(self.panel, choices=[])
        self.city_choice.Bind(wx.EVT_CHOICE, self.show_weather)
        self.city_choice_text = wx.StaticText(self.panel, label="Choose city")

        self.vbox.Add(self.city_choice_text, 0, wx.ALL | wx.EXPAND, 5)
        self.vbox.Add(self.city_choice, 0, wx.ALL | wx.EXPAND, 5)
        self.city_choice.Hide()
        self.city_choice_text.Hide()

        self.weather_panel = wx.Panel(self.panel)
        weather_box = wx.StaticBox(self.weather_panel, label="Weather Info")
        weather_box_sizer = wx.StaticBoxSizer(weather_box, wx.VERTICAL)

        self.grid = wx.grid.Grid(self.weather_panel)
        weather_box_sizer.Add(self.grid, 1, wx.ALL | wx.EXPAND, 5)

        self.weather_panel.SetSizer(weather_box_sizer)
        self.vbox.Add(self.weather_panel, 1, wx.ALL | wx.EXPAND, 5)

        self.search_history = []  # Przechowuje historię wyszukiwania
        self.create_empty_grid()  # Tworzy pustą tabelę

        self.panel.SetSizer(self.vbox)
        self.Center()
        self.Show()

    def create_empty_grid(self):
        self.grid.CreateGrid(0, 3)
        self.grid.SetColLabelValue(0, 'Country')
        self.grid.SetColLabelValue(1, 'Current temperature (°C)')
        self.grid.SetColLabelValue(2, 'Is day')

        self.grid.AutoSizeColumns()

    def on_country_selected(self, event):
        busy_info = wx.BusyInfo("Please wait...")
        selected_country = self.country_choices[event.GetSelection()]
        selected_cities = self.df.loc[self.df['country'] == selected_country, 'city'].tolist()
        self.city_choice.SetItems(selected_cities)
        self.city_choice.Show()
        self.city_choice_text.Show()
        self.vbox.Layout()
        del busy_info

    def show_weather(self, event):
        selected_city = event.GetString()
        self.show_current_weather(selected_city)

    def show_current_weather(self, city):
        cache_session = requests_cache.CachedSession('.cache', expire_after=3600)
        retry_session = retry(cache_session, retries=5, backoff_factor=0.2)
        openmeteo = openmeteo_requests.Client(session=retry_session)
        geolocator = Nominatim(user_agent="my_geocoder")
        geocode = geolocator.geocode(city)

        url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": geocode.latitude,
            "longitude": geocode.longitude,
            "current": ["temperature_2m", 'is_day']
        }
        responses = openmeteo.weather_api(url, params=params)
        response = responses[0]
        current = response.Current()
        current_temperature_2m = current.Variables(0).Value()
        current_is_day = current.Variables(1).Value()
        current_temperature_2m = round(current_temperature_2m, 2)

        self.update_grid(city, current_temperature_2m, current_is_day)

    def update_grid(self, city, temperature, is_day):
        self.grid.AppendRows(1)
        row_count = self.grid.GetNumberRows()

        self.grid.SetCellValue(row_count - 1, 0, city)
        self.grid.SetCellValue(row_count - 1, 1, str(temperature))
        self.grid.SetCellValue(row_count - 1, 2, str(is_day))  # Ustawiamy wartość is_day


        # Ustawianie ikonki w zależności od wartości is_day
        if is_day == 1.0:
            icon_path = "sun_icon.png"  # Dodaj odpowiednią ścieżkę do ikony słońca
        else:
            icon_path = "moon_icon.png"  # Dodaj odpowiednią ścieżkę do ikony księżyca

        img = wx.Image(icon_path, wx.BITMAP_TYPE_ANY)
        img.Rescale(16, 16)
        bmp = wx.Bitmap(img)

        renderer = MyRenderer(bmp)
        self.grid.SetCellRenderer(row_count - 1, 2, renderer)

        editor = wx.grid.GridCellBoolEditor()
        self.grid.SetCellEditor(row_count - 1, 2, editor)

        self.grid.AutoSizeColumns()

        # Dodaj wpis do historii wyszukiwania
        self.search_history.append((city, temperature, is_day))


class MyRenderer(wx.grid.GridCellRenderer):
    def __init__(self, bitmap):
        wx.grid.GridCellRenderer.__init__(self)
        self.bitmap = bitmap

    def Draw(self, grid, attr, dc, rect, row, col, isSelected):
        imageRect = wx.Rect(*rect)
        imageRect.Deflate(1, 1)

        img = self.bitmap
        if img.IsOk():
            dc.DrawBitmap(img, imageRect.x, imageRect.y, True)

    def GetBestSize(self, grid, attr, dc, row, col):
        return wx.Size(20, 20)


if __name__ == '__main__':
    df = pd.read_excel('worldcities.xlsx')  # Wczytanie ramki danych z pliku Excel
    app = wx.App()
    frame = MyFrame(None, "Weather app", df)  # Przekazanie ramki danych do panelu
    app.MainLoop()
