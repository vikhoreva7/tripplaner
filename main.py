import threading
import sqlite3
import requests
import json
import time
from datetime import datetime, timedelta
import random
import os

from kivy.app import App
from kivy.lang import Builder
from kivy.clock import mainthread
from kivy.uix.screenmanager import ScreenManager, Screen, SlideTransition
from kivy.properties import StringProperty, ListProperty, ObjectProperty, NumericProperty
from kivy.uix.popup import Popup
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.scrollview import ScrollView
from kivy.uix.gridlayout import GridLayout
from kivy.uix.image import Image
from kivy.core.window import Window
from kivy.metrics import dp
from kivy.graphics import Color, RoundedRectangle, Rectangle

try:
    from plyer import notification
except Exception:
    notification = None

Window.size = (360, 640)

try:
    from kivy_garden.mapview import MapView, MapMarker

    MAP_AVAILABLE = True
except ImportError:
    MAP_AVAILABLE = False
    print("MapView не установлен. Установите: pip install kivy_garden.mapview")

OWM_API_KEY = "cfdbf075ac434def535eca5067ea6f2d"
SERVER_URL = "https://example.com/api"
SYNC_INTERVAL_SECONDS = 60 * 5
DB_PATH = "travelmate.db"

KV = """
#:import utils kivy.utils
#:set PRIMARY_COLOR 0.2, 0.6, 0.8, 1
#:set SECONDARY_COLOR 0.9, 0.95, 1, 1
#:set ACCENT_COLOR 1, 0.8, 0.2, 1
#:set DANGER_COLOR 0.9, 0.3, 0.3, 1
#:set SUCCESS_COLOR 0.3, 0.7, 0.4, 1
#:set WEATHER_SUNNY 1, 0.8, 0.2, 1
#:set WEATHER_CLOUDY 0.7, 0.8, 0.9, 1
#:set WEATHER_RAINY 0.4, 0.6, 0.9, 1

<WeatherCard@BoxLayout>:
    orientation: 'vertical'
    padding: dp(15)
    spacing: dp(10)
    size_hint_y: None
    height: dp(120)
    canvas.before:
        Color:
            rgba: 1, 1, 1, 1
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [dp(20)]
        Color:
            rgba: SECONDARY_COLOR
        RoundedRectangle:
            pos: self.pos[0]+dp(1), self.pos[1]+dp(1)
            size: self.size[0]-dp(2), self.size[1]-dp(2)
            radius: [dp(19)]

<WeatherValue@BoxLayout>:
    orientation: 'horizontal'
    size_hint_y: None
    height: dp(25)
    spacing: dp(8)
    Label:
        text: root.icon
        font_size: dp(16)
        size_hint_x: None
        width: dp(25)
    Label:
        text: root.label
        font_size: dp(14)
        color: 0.4, 0.4, 0.4, 1
        size_hint_x: None
        width: dp(100)
        halign: 'left'
    Label:
        text: root.value
        font_size: dp(14)
        bold: True
        color: PRIMARY_COLOR
        halign: 'right'

<GradientButton@Button>:
    background_color: 0, 0, 0, 0
    background_normal: ''
    canvas.before:
        Color:
            rgba: PRIMARY_COLOR
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [dp(15)]
        Color:
            rgba: 1, 1, 1, 0.1
        RoundedRectangle:
            pos: self.pos[0], self.pos[1]
            size: self.size[0], self.size[1]
            radius: [dp(15)]

<CardLayout@BoxLayout>:
    orientation: 'vertical'
    padding: dp(15)
    spacing: dp(10)
    canvas.before:
        Color:
            rgba: 1, 1, 1, 1
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [dp(20)]
        Color:
            rgba: SECONDARY_COLOR
        RoundedRectangle:
            pos: self.pos[0]+dp(1), self.pos[1]+dp(1)
            size: self.size[0]-dp(2), self.size[1]-dp(2)
            radius: [dp(19)]

<RouteButton@Button>:
    background_color: 0, 0, 0, 0
    background_normal: ''
    canvas.before:
        Color:
            rgba: 1, 1, 1, 1
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [dp(15)]
        Color:
            rgba: SECONDARY_COLOR
        RoundedRectangle:
            pos: self.pos[0]+dp(1), self.pos[1]+dp(1)
            size: self.size[0]-dp(2), self.size[1]-dp(2)
            radius: [dp(14)]
    BoxLayout:
        orientation: 'vertical'
        padding: dp(10)
        spacing: dp(5)
        Label:
            text: root.text.split('\\n')[0]
            font_size: dp(16)
            bold: True
            color: 0.2, 0.2, 0.2, 1
            text_size: self.width, None
            halign: 'left'
            valign: 'top'
        Label:
            text: root.text.split('\\n')[1] if len(root.text.split('\\n')) > 1 else ''
            font_size: dp(12)
            color: 0.5, 0.5, 0.5, 1
            text_size: self.width, None
            halign: 'left'
            valign: 'top'

<MsgPopup>:
    size_hint: 0.8, 0.4
    auto_dismiss: False
    background: ''
    title: ''
    title_size: 0
    BoxLayout:
        orientation: "vertical"
        padding: dp(20)
        spacing: dp(15)
        canvas.before:
            Color:
                rgba: 1, 1, 1, 1
            RoundedRectangle:
                pos: self.pos
                size: self.size
                radius: [dp(25)]
            Color:
                rgba: SECONDARY_COLOR
            RoundedRectangle:
                pos: self.pos[0]+dp(2), self.pos[1]+dp(2)
                size: self.size[0]-dp(4), self.size[1]-dp(4)
                radius: [dp(23)]
        Label:
            text: root.title
            font_size: dp(18)
            bold: True
            color: PRIMARY_COLOR
            size_hint_y: None
            height: dp(30)
        Label:
            text: root.message
            font_size: dp(14)
            color: 0.3, 0.3, 0.3, 1
            text_size: self.width, None
        GradientButton:
            text: "ОК"
            size_hint_y: None
            height: dp(40)
            font_size: dp(16)
            on_release: root.dismiss()

<WeatherScreen>:
    location_input: location_input
    weather_container: weather_container
    BoxLayout:
        orientation: "vertical"
        padding: dp(15)
        spacing: dp(10)  
        canvas.before:
            Color:
                rgba: SECONDARY_COLOR
            Rectangle:
                pos: self.pos
                size: self.size
        Label:
            text: "Погода"
            font_size: dp(22)
            bold: True
            color: PRIMARY_COLOR
            size_hint_y: None
            height: dp(30)
        CardLayout:
            orientation: 'vertical'
            spacing: dp(12)
            padding: dp(15)
            size_hint_y: None
            height: dp(120)  
            BoxLayout:
                size_hint_y: None
                height: dp(45)
                spacing: dp(8)
                TextInput:
                    id: location_input
                    hint_text: "Введите город (например: Moscow)"
                    multiline: False
                    font_size: dp(14)
                    background_normal: ''
                    background_active: ''
                    background_color: 0.95, 0.95, 0.95, 1
                    padding: [dp(15), dp(12)]
                GradientButton:
                    text: "🔍"
                    size_hint_x: None
                    width: dp(50)
                    font_size: dp(16)
                    on_release: root.get_weather()
        
        ScrollView:
            do_scroll_x: False
            BoxLayout:
                id: weather_container
                orientation: 'vertical'
                spacing: dp(10)
                padding: dp(5)
                size_hint_y: None
                height: self.minimum_height
        
        GradientButton:
            text: "Домой"
            size_hint_y: None
            height: dp(45)
            font_size: dp(16)
            on_release: app.root.current = "home"

<LoginScreen>:
    email_input: email_input
    password_input: password_input
    BoxLayout:
        orientation: "vertical"
        padding: dp(30)
        spacing: dp(20)
        canvas.before:
            Color:
                rgba: PRIMARY_COLOR
            Rectangle:
                pos: self.pos
                size: self.size
        BoxLayout:
            orientation: 'vertical'
            spacing: dp(10)
            size_hint_y: None
            height: dp(120)
            Label:
                text: "TravelMate"
                font_size: dp(32)
                bold: True
                color: 1, 1, 1, 1
                size_hint_y: None
                height: dp(50)
            Label:
                text: "Ваш личный гид"
                font_size: dp(16)
                color: 1, 1, 1, 0.8
                size_hint_y: None
                height: dp(25)
        CardLayout:
            orientation: 'vertical'
            spacing: dp(15)
            padding: dp(20)
            size_hint_y: None
            height: dp(280)
            Label:
                text: "Вход в систему"
                font_size: dp(20)
                bold: True
                color: PRIMARY_COLOR
                size_hint_y: None
                height: dp(30)
            TextInput:
                id: email_input
                hint_text: "Email"
                multiline: False
                font_size: dp(16)
                size_hint_y: None
                height: dp(45)
                background_normal: ''
                background_active: ''
                background_color: 0.95, 0.95, 0.95, 1
                padding: [dp(15), dp(12)]
            TextInput:
                id: password_input
                hint_text: "Пароль"
                password: True
                multiline: False
                font_size: dp(16)
                size_hint_y: None
                height: dp(45)
                background_normal: ''
                background_active: ''
                background_color: 0.95, 0.95, 0.95, 1
                padding: [dp(15), dp(12)]
            GradientButton:
                text: "Войти"
                size_hint_y: None
                height: dp(50)
                font_size: dp(16)
                on_release: root.do_login()
            BoxLayout:
                size_hint_y: None
                height: dp(40)
                spacing: dp(10)
                Button:
                    text: "Регистрация"
                    background_color: 0, 0, 0, 0
                    color: PRIMARY_COLOR
                    font_size: dp(14)
                    on_release: app.root.current = "register"
                Button:
                    text: "Демо вход"
                    background_color: 0, 0, 0, 0
                    color: ACCENT_COLOR
                    font_size: dp(14)
                    on_release: root.fill_demo()

<RegisterScreen>:
    name_input: name_input
    email_input: email_input
    password_input: password_input
    BoxLayout:
        orientation: "vertical"
        padding: dp(20)
        spacing: dp(15)
        canvas.before:
            Color:
                rgba: PRIMARY_COLOR
            Rectangle:
                pos: self.pos
                size: self.size
        Button:
            text: "← Назад"
            size_hint: None, None
            size: dp(80), dp(40)
            pos_hint: {'top': 1, 'left': 1}
            background_color: 0, 0, 0, 0
            color: 1, 1, 1, 1
            font_size: dp(14)
            on_release: app.root.current = "login"
        CardLayout:
            orientation: 'vertical'
            spacing: dp(15)
            padding: dp(20)
            Label:
                text: "Регистрация"
                font_size: dp(22)
                bold: True
                color: PRIMARY_COLOR
                size_hint_y: None
                height: dp(35)
            TextInput:
                id: name_input
                hint_text: "👤 Имя"
                multiline: False
                font_size: dp(16)
                size_hint_y: None
                height: dp(45)
                background_normal: ''
                background_active: ''
                background_color: 0.95, 0.95, 0.95, 1
                padding: [dp(15), dp(12)]
            TextInput:
                id: email_input
                hint_text: "Email"
                multiline: False
                font_size: dp(16)
                size_hint_y: None
                height: dp(45)
                background_normal: ''
                background_active: ''
                background_color: 0.95, 0.95, 0.95, 1
                padding: [dp(15), dp(12)]
            TextInput:
                id: password_input
                hint_text: "Пароль"
                password: True
                multiline: False
                font_size: dp(16)
                size_hint_y: None
                height: dp(45)
                background_normal: ''
                background_active: ''
                background_color: 0.95, 0.95, 0.95, 1
                padding: [dp(15), dp(12)]
            GradientButton:
                text: "Создать аккаунт"
                size_hint_y: None
                height: dp(50)
                font_size: dp(16)
                on_release: root.do_register()

<HomeScreen>:
    username_label: username_label
    BoxLayout:
        orientation: "vertical"
        padding: dp(15)
        spacing: dp(10)
        canvas.before:
            Color:
                rgba: SECONDARY_COLOR
            Rectangle:
                pos: self.pos
                size: self.size
        BoxLayout:
            size_hint_y: None
            height: dp(60)
            spacing: dp(10)
            Label:
                id: username_label
                text: "Привет, гость!"
                font_size: dp(20)
                bold: True
                color: PRIMARY_COLOR
                text_size: self.width, None
                halign: 'left'
                valign: 'middle'
            Button:
                text: "⚙️"
                size_hint: None, None
                size: dp(50), dp(50)
                background_color: 0, 0, 0, 0
                color: PRIMARY_COLOR
                font_size: dp(20)
                on_release: app.root.current = "settings"
        GridLayout:
            cols: 2
            spacing: dp(10)
            size_hint_y: None
            height: dp(200)
            GradientButton:
                text: "️\\nМаршруты"
                font_size: dp(16)
                on_release: app.root.current = "routes"
            GradientButton:
                text: "\\nКарта"
                font_size: dp(16)
                on_release: app.root.current = "map"
            GradientButton:
                text: "\\nПогода"
                font_size: dp(16)
                on_release: app.root.current = "weather"
            GradientButton:
                text: "\\nИзбранное"
                font_size: dp(16)
                on_release: app.root.current = "favorites"
        CardLayout:
            orientation: 'vertical'
            spacing: dp(10)
            padding: dp(15)
            size_hint_y: None
            height: dp(120)
            Label:
                text: "Быстрые действия"
                font_size: dp(16)
                bold: True
                color: PRIMARY_COLOR
                size_hint_y: None
                height: dp(25)
            BoxLayout:
                spacing: dp(10)
                GradientButton:
                    text: "Синхронизация"
                    font_size: dp(14)
                    on_release: root.manual_sync()
                GradientButton:
                    text: "Выйти"
                    font_size: dp(14)
                    background_color: DANGER_COLOR
                    on_release: root.logout()

<MapScreen>:
    map_layout: map_layout
    BoxLayout:
        orientation: "vertical"
        spacing: dp(5)
        canvas.before:
            Color:
                rgba: SECONDARY_COLOR
            Rectangle:
                pos: self.pos
                size: self.size
        BoxLayout:
            size_hint_y: None
            height: dp(50)
            spacing: dp(5)
            padding: dp(5)
            GradientButton:
                text: "Москва"
                font_size: dp(12)
                on_release: root.set_location(55.7558, 37.6173, "Москва")
            GradientButton:
                text: "СПб"
                font_size: dp(12)
                on_release: root.set_location(59.9343, 30.3351, "Санкт-Петербург")
            GradientButton:
                text: "Сочи"
                font_size: dp(12)
                on_release: root.set_location(43.5855, 39.7231, "Сочи")
        BoxLayout:
            orientation: "vertical"
            id: map_layout
        BoxLayout:
            size_hint_y: None
            height: dp(50)
            spacing: dp(5)
            padding: dp(5)
            GradientButton:
                text: "Мои маршруты"
                font_size: dp(12)
                on_release: root.show_my_routes()
            GradientButton:
                text: "Новый"
                font_size: dp(12)
                on_release: app.root.current = "newroute"
            GradientButton:
                text: "Домой"
                font_size: dp(12)
                on_release: app.root.current = "home"

<RoutesScreen>:
    search_input: search_input
    routes_box: routes_box
    BoxLayout:
        orientation: "vertical"
        padding: dp(10)
        spacing: dp(10)
        canvas.before:
            Color:
                rgba: SECONDARY_COLOR
            Rectangle:
                pos: self.pos
                size: self.size
        BoxLayout:
            size_hint_y: None
            height: dp(50)
            spacing: dp(10)
            TextInput:
                id: search_input
                hint_text: "Поиск маршрутов..."
                multiline: False
                font_size: dp(14)
                background_normal: ''
                background_active: ''
                background_color: 1, 1, 1, 1
                padding: [dp(10), dp(8)]
            GradientButton:
                text: "Поиск"
                size_hint_x: None
                width: dp(80)
                font_size: dp(14)
                on_release: root.do_search()
        ScrollView:
            do_scroll_x: False
            GridLayout:
                id: routes_box
                cols: 1
                size_hint_y: None
                height: self.minimum_height
                spacing: dp(8)
                padding: dp(5)
        BoxLayout:
            size_hint_y: None
            height: dp(50)
            spacing: dp(10)
            GradientButton:
                text: "Домой"
                font_size: dp(14)
                on_release: app.root.current = "home"
            GradientButton:
                text: "Новый маршрут"
                font_size: dp(14)
                on_release: app.root.current = "newroute"

<NewRouteScreen>:
    route_name_input: route_name_input
    desc_input: desc_input
    lat_input: lat_input
    lon_input: lon_input
    BoxLayout:
        orientation: "vertical"
        padding: dp(15)
        spacing: dp(15)
        canvas.before:
            Color:
                rgba: SECONDARY_COLOR
            Rectangle:
                pos: self.pos
                size: self.size
        Label:
            text: "Новый маршрут"
            font_size: dp(22)
            bold: True
            color: PRIMARY_COLOR
            size_hint_y: None
            height: dp(30)
        CardLayout:
            orientation: 'vertical'
            spacing: dp(12)
            padding: dp(15)
            TextInput:
                id: route_name_input
                hint_text: "Название маршрута"
                multiline: False
                font_size: dp(16)
                size_hint_y: None
                height: dp(45)
                background_normal: ''
                background_active: ''
                background_color: 0.95, 0.95, 0.95, 1
            TextInput:
                id: desc_input
                hint_text: "Описание маршрута"
                font_size: dp(14)
                size_hint_y: None
                height: dp(80)
                background_normal: ''
                background_active: ''
                background_color: 0.95, 0.95, 0.95, 1
            BoxLayout:
                size_hint_y: None
                height: dp(40)
                spacing: dp(8)
                TextInput:
                    id: lat_input
                    hint_text: "Широта"
                    multiline: False
                    font_size: dp(12)
                    background_normal: ''
                    background_active: ''
                    background_color: 0.95, 0.95, 0.95, 1
                TextInput:
                    id: lon_input
                    hint_text: "Долгота"
                    multiline: False
                    font_size: dp(12)
                    background_normal: ''
                    background_active: ''
                    background_color: 0.95, 0.95, 0.95, 1
            GradientButton:
                text: "Выбрать на карте"
                size_hint_y: None
                height: dp(40)
                font_size: dp(14)
                on_release: root.choose_on_map()
        BoxLayout:
            size_hint_y: None
            height: dp(50)
            spacing: dp(10)
            GradientButton:
                text: "Сохранить"
                font_size: dp(16)
                on_release: root.save_route()
            GradientButton:
                text: "Отмена"
                font_size: dp(16)
                background_color: DANGER_COLOR
                on_release: app.root.current = "routes"

<RouteDetailScreen>:
    route_name: route_name
    route_desc: route_desc
    route_coords: route_coords
    BoxLayout:
        orientation: "vertical"
        padding: dp(15)
        spacing: dp(15)
        canvas.before:
            Color:
                rgba: SECONDARY_COLOR
            Rectangle:
                pos: self.pos
                size: self.size
        CardLayout:
            orientation: 'vertical'
            spacing: dp(12)
            padding: dp(15)
            Label:
                id: route_name
                text: "Маршрут"
                font_size: dp(20)
                bold: True
                color: PRIMARY_COLOR
                size_hint_y: None
                height: dp(30)
            Label:
                id: route_desc
                text: "Описание"
                font_size: dp(14)
                color: 0.4, 0.4, 0.4, 1
                text_size: self.width, None
            Label:
                id: route_coords
                text: "Координаты: не указаны"
                font_size: dp(12)
                color: 0.6, 0.6, 0.6, 1
                size_hint_y: None
                height: dp(20)
        GridLayout:
            cols: 2
            spacing: dp(8)
            size_hint_y: None
            height: dp(100)
            GradientButton:
                text: "\\nВ избранное"
                font_size: dp(12)
                on_release: root.add_favorite()
            GradientButton:
                text: "\\nНапомнить"
                font_size: dp(12)
                on_release: root.schedule_reminder()
            GradientButton:
                text: "\\nНа карте"
                font_size: dp(12)
                on_release: root.show_on_map()
            GradientButton:
                text: "\\nСтатистика"
                font_size: dp(12)
                on_release: root.show_stats()
        GradientButton:
            text: "← Назад к маршрутам"
            size_hint_y: None
            height: dp(45)
            font_size: dp(16)
            on_release: app.root.current = "routes"

<FavoritesScreen>:
    fav_box: fav_box
    BoxLayout:
        orientation: "vertical"
        padding: dp(15)
        spacing: dp(15)
        canvas.before:
            Color:
                rgba: SECONDARY_COLOR
            Rectangle:
                pos: self.pos
                size: self.size
        Label:
            text: "Избранное"
            font_size: dp(22)
            bold: True
            color: PRIMARY_COLOR
            size_hint_y: None
            height: dp(30)
        ScrollView:
            do_scroll_x: False
            GridLayout:
                id: fav_box
                cols: 1
                size_hint_y: None
                height: self.minimum_height
                spacing: dp(8)
                padding: dp(5)
        GradientButton:
            text: "Домой"
            size_hint_y: None
            height: dp(45)
            font_size: dp(16)
            on_release: app.root.current = "home"

<SettingsScreen>:
    BoxLayout:
        orientation: "vertical"
        padding: dp(15)
        spacing: dp(15)
        canvas.before:
            Color:
                rgba: SECONDARY_COLOR
            Rectangle:
                pos: self.pos
                size: self.size
        Label:
            text: "Настройки"
            font_size: dp(22)
            bold: True
            color: PRIMARY_COLOR
            size_hint_y: None
            height: dp(30)
        CardLayout:
            orientation: 'vertical'
            spacing: dp(10)
            padding: dp(15)
            GradientButton:
                text: "Синхронизировать"
                font_size: dp(16)
                on_release: root.sync_now()
            GradientButton:
                text: "Статистика"
                font_size: dp(16)
                on_release: root.show_stats()
            GradientButton:
                text: "Очистить данные"
                font_size: dp(16)
                background_color: DANGER_COLOR
                on_release: root.clear_local()
        GradientButton:
            text: "Домой"
            size_hint_y: None
            height: dp(45)
            font_size: dp(16)
            on_release: app.root.current = "home"

ScreenManager:
    id: screen_manager
    LoginScreen:
        name: "login"
    RegisterScreen:
        name: "register"
    HomeScreen:
        name: "home"
    MapScreen:
        name: "map"
    RoutesScreen:
        name: "routes"
    NewRouteScreen:
        name: "newroute"
    RouteDetailScreen:
        name: "routedetail"
    WeatherScreen:
        name: "weather"
    FavoritesScreen:
        name: "favorites"
    SettingsScreen:
        name: "settings"
"""


class WeatherValue(BoxLayout):
    icon = StringProperty("")
    label = StringProperty("")
    value = StringProperty("")


class WeatherCard(BoxLayout):
    pass


class MsgPopup(Popup):
    title = StringProperty("Сообщение")
    message = StringProperty("")


class LocalDB:
    def __init__(self, path=DB_PATH):
        self.path = path
        if os.path.exists(path):
            os.remove(path)
        self.conn = sqlite3.connect(self.path, check_same_thread=False)
        self.init_db()

    def init_db(self):
        cur = self.conn.cursor()
        cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            email TEXT UNIQUE,
            password TEXT,
            token TEXT,
            created_at TEXT
        )""")

        cur.execute("""
        CREATE TABLE IF NOT EXISTS routes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            name TEXT,
            description TEXT,
            latitude REAL,
            longitude REAL,
            created_at TEXT,
            synced INTEGER DEFAULT 0
        )""")
        cur.execute("""
        CREATE TABLE IF NOT EXISTS favorites (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            route_id INTEGER,
            created_at TEXT
        )""")
        self.conn.commit()

    def create_user(self, name, email, password):
        cur = self.conn.cursor()
        try:
            cur.execute("INSERT INTO users (name, email, password, created_at) VALUES (?, ?, ?, ?)",
                        (name, email, password, datetime.utcnow().isoformat()))
            self.conn.commit()
            return cur.lastrowid
        except sqlite3.IntegrityError:
            return None

    def authenticate(self, email, password):
        cur = self.conn.cursor()
        cur.execute("SELECT id, name FROM users WHERE email=? AND password=?", (email, password))
        row = cur.fetchone()
        return row

    def store_token(self, user_id, token):
        cur = self.conn.cursor()
        cur.execute("UPDATE users SET token=? WHERE id=?", (token, user_id))
        self.conn.commit()

    def get_user(self, user_id):
        cur = self.conn.cursor()
        cur.execute("SELECT id, name, email FROM users WHERE id=?", (user_id,))
        return cur.fetchone()

    def save_route(self, user_id, name, description, latitude=None, longitude=None):
        cur = self.conn.cursor()
        cur.execute("""INSERT INTO routes 
                    (user_id, name, description, latitude, longitude, created_at, synced) 
                    VALUES (?, ?, ?, ?, ?, ?, 0)""",
                    (user_id, name, description, latitude, longitude, datetime.utcnow().isoformat()))
        self.conn.commit()
        return cur.lastrowid

    def list_routes(self, user_id, query=None):
        cur = self.conn.cursor()
        if query:
            q = f"%{query}%"
            cur.execute(
                "SELECT id, name, description, latitude, longitude, created_at FROM routes WHERE user_id=? AND (name LIKE ? OR description LIKE ?) ORDER BY created_at DESC",
                (user_id, q, q))
        else:
            cur.execute(
                "SELECT id, name, description, latitude, longitude, created_at FROM routes WHERE user_id=? ORDER BY created_at DESC",
                (user_id,))
        return cur.fetchall()

    def get_route(self, route_id):
        cur = self.conn.cursor()
        cur.execute("SELECT id, user_id, name, description, latitude, longitude, created_at FROM routes WHERE id=?",
                    (route_id,))
        return cur.fetchone()

    def add_favorite(self, user_id, route_id):
        cur = self.conn.cursor()
        cur.execute("SELECT id FROM favorites WHERE user_id=? AND route_id=?", (user_id, route_id))
        if not cur.fetchone():
            cur.execute("INSERT INTO favorites (user_id, route_id, created_at) VALUES (?, ?, ?)",
                        (user_id, route_id, datetime.utcnow().isoformat()))
            self.conn.commit()
            return True
        return False

    def list_favorites(self, user_id):
        cur = self.conn.cursor()
        cur.execute(
            "SELECT r.id, r.name, r.description, r.latitude, r.longitude FROM favorites f JOIN routes r ON f.route_id=r.id WHERE f.user_id=? ORDER BY f.created_at DESC",
            (user_id,))
        return cur.fetchall()

    def get_unsynced_routes(self, user_id):
        cur = self.conn.cursor()
        cur.execute(
            "SELECT id, name, description, latitude, longitude, created_at FROM routes WHERE user_id=? AND synced=0",
            (user_id,))
        return cur.fetchall()

    def mark_route_synced(self, route_id):
        cur = self.conn.cursor()
        cur.execute("UPDATE routes SET synced=1 WHERE id=?", (route_id,))
        self.conn.commit()

    def get_user_stats(self, user_id):
        cur = self.conn.cursor()
        cur.execute("SELECT COUNT(*) FROM routes WHERE user_id=?", (user_id,))
        route_count = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM favorites WHERE user_id=?", (user_id,))
        fav_count = cur.fetchone()[0]

        cur.execute("SELECT name, created_at FROM routes WHERE user_id=? ORDER BY created_at DESC LIMIT 1", (user_id,))
        last_route = cur.fetchone()

        return {
            'route_count': route_count,
            'fav_count': fav_count,
            'last_route': last_route
        }

    def clear_all(self):
        cur = self.conn.cursor()
        cur.execute("DELETE FROM routes")
        cur.execute("DELETE FROM favorites")
        self.conn.commit()


class WeatherScreen(Screen):
    location_input = ObjectProperty(None)
    weather_container = ObjectProperty(None)

    def get_weather(self):
        loc = self.location_input.text.strip()
        if not loc:
            MsgPopup(title="Ошибка", message="Введите город").open()
            return
        threading.Thread(target=self._fetch_weather, args=(loc,), daemon=True).start()

    def _fetch_weather(self, loc):
        app = self.manager.app
        try:
            if not OWM_API_KEY:
                raise RuntimeError("OWM_API_KEY не настроен")
            url = f"https://api.openweathermap.org/data/2.5/weather"
            params = {"q": loc, "appid": OWM_API_KEY, "units": "metric", "lang": "ru"}
            r = requests.get(url, params=params, timeout=10)
            r.raise_for_status()
            data = r.json()
            self.display_weather_data(data, loc)
        except Exception as e:
            self.show_weather_error(f"Ошибка получения погоды: {str(e)}")

    def display_weather_data(self, data, location):
        weather_info = {
            'location': location,
            'description': data["weather"][0]["description"].capitalize(),
            'temperature': f"{data['main']['temp']:.1f}°C",
            'feels_like': f"{data['main']['feels_like']:.1f}°C",
            'humidity': f"{data['main']['humidity']}%",
            'pressure': f"{data['main']['pressure']} hPa",
            'wind_speed': f"{data['wind']['speed']} м/с",
            'visibility': f"{data.get('visibility', 0) / 1000:.1f} км",
            'clouds': f"{data['clouds']['all']}%"
        }

        self.update_weather_display(weather_info)

    @mainthread
    def update_weather_display(self, weather_info):
        self.weather_container.clear_widgets()

        main_card = WeatherCard()

        location_label = Label(
            text=f"{weather_info['location']}",
            font_size=dp(18),
            bold=True,
            color=(0.2, 0.2, 0.2, 1),
            size_hint_y=None,
            height=dp(30)
        )
        main_card.add_widget(location_label)

        desc_label = Label(
            text=weather_info['description'],
            font_size=dp(16),
            color=(0.4, 0.4, 0.4, 1),
            size_hint_y=None,
            height=dp(25)
        )
        main_card.add_widget(desc_label)

        temp_label = Label(
            text=weather_info['temperature'],
            font_size=dp(32),
            bold=True,
            color=(0.2, 0.6, 0.8, 1),
            size_hint_y=None,
            height=dp(40)
        )
        main_card.add_widget(temp_label)

        self.weather_container.add_widget(main_card)

        details_card = WeatherCard()
        details_card.height = dp(180)

        details_grid = GridLayout(cols=2, spacing=dp(10), size_hint_y=None, height=dp(140))

        details = [
            ("🌡️", "Ощущается", weather_info['feels_like']),
            ("💧", "Влажность", weather_info['humidity']),
            ("🌬️", "Ветер", weather_info['wind_speed']),
            ("☁️", "Облачность", weather_info['clouds']),
            ("🔍", "Видимость", weather_info['visibility']),
            ("📊", "Давление", weather_info['pressure'])
        ]

        for icon, label, value in details:
            weather_value = WeatherValue(icon=icon, label=label, value=value)
            details_grid.add_widget(weather_value)

        details_card.add_widget(details_grid)
        self.weather_container.add_widget(details_card)

    @mainthread
    def show_weather_error(self, error_message):
        self.weather_container.clear_widgets()

        error_card = WeatherCard()
        error_card.height = dp(100)

        error_label = Label(
            text=error_message,
            font_size=dp(14),
            color=(0.9, 0.3, 0.3, 1),
            text_size=(Window.width - dp(50), None),
            halign='center',
            valign='middle'
        )
        error_card.add_widget(error_label)
        self.weather_container.add_widget(error_card)



class MapScreen(Screen):
    map_layout = ObjectProperty(None)
    current_marker = None

    def on_pre_enter(self):
        self.setup_map()

    def setup_map(self):
        if not MAP_AVAILABLE:
            self.show_map_error()
            return

        self.map_layout.clear_widgets()
        self.map_view = MapView(zoom=10, lat=55.7558, lon=37.6173)
        self.map_layout.add_widget(self.map_view)

        self.add_marker(55.7558, 37.6173, "Москва")

    def show_map_error(self):
        self.map_layout.clear_widgets()
        error_layout = BoxLayout(orientation='vertical', padding=20)
        error_layout.add_widget(Label(
            text="Карта недоступна\n\nУстановите MapView:\npip install kivy_garden.mapview",
            halign='center'
        ))
        self.map_layout.add_widget(error_layout)

    def add_marker(self, lat, lon, title=""):
        if not MAP_AVAILABLE:
            return

        marker = MapMarker(lat=lat, lon=lon)
        self.map_view.add_marker(marker)
        self.current_marker = marker

    def set_location(self, lat, lon, title=""):
        if not MAP_AVAILABLE:
            return

        self.map_view.center_on(lat, lon)
        self.map_view.zoom = 12

        if self.current_marker:
            self.map_view.remove_marker(self.current_marker)

        self.add_marker(lat, lon, title)

    def show_my_routes(self):
        if not MAP_AVAILABLE:
            return

        app = self.manager.app
        if not app.current_user:
            return

        if self.current_marker:
            self.map_view.remove_marker(self.current_marker)
            self.current_marker = None

        uid = app.current_user["id"]
        routes = app.db.list_routes(uid)

        if routes:
            first_route = routes[0]
            lat, lon = first_route[3], first_route[4]
            if lat and lon:
                self.map_view.center_on(lat, lon)
                self.map_view.zoom = 8

            for route in routes:
                rid, name, desc, lat, lon, created = route
                if lat and lon:
                    self.add_marker(lat, lon, name)

            MsgPopup(title="🗺️ Маршруты", message=f"Показано {len(routes)} маршрутов на карте").open()
        else:
            MsgPopup(title="🗺️ Маршруты", message="У вас пока нет маршрутов").open()


class LoginScreen(Screen):
    email_input = ObjectProperty(None)
    password_input = ObjectProperty(None)

    def on_pre_enter(self):
        if self.email_input:
            self.email_input.text = ""
        if self.password_input:
            self.password_input.text = ""

    def do_login(self):
        email = self.email_input.text.strip()
        password = self.password_input.text.strip()
        if not email or not password:
            MsgPopup(title="Ошибка", message="Введите email и пароль").open()
            return
        db = self.manager.app.db
        row = db.authenticate(email, password)
        if row:
            user_id, name = row
            self.manager.app.current_user = {"id": user_id, "name": name, "email": email}
            token = f"local-token-{user_id}-{int(time.time())}"
            db.store_token(user_id, token)
            self.manager.current = "home"
            self.manager.get_screen("home").on_enter()
        else:
            MsgPopup(title="Ошибка", message="Неверный email или пароль").open()

    def fill_demo(self):
        db = self.manager.app.db
        demo_email = "demo@travelmate.local"
        demo_pass = "demo"
        cur = db.conn.cursor()
        cur.execute("SELECT id,name FROM users WHERE email=?", (demo_email,))
        r = cur.fetchone()
        if not r:
            db.create_user("Demo User", demo_email, demo_pass)
        self.email_input.text = demo_email
        self.password_input.text = demo_pass


class RegisterScreen(Screen):
    name_input = ObjectProperty(None)
    email_input = ObjectProperty(None)
    password_input = ObjectProperty(None)

    def do_register(self):
        name = self.name_input.text.strip()
        email = self.email_input.text.strip()
        password = self.password_input.text.strip()
        if not name or not email or not password:
            MsgPopup(title="Ошибка", message="Заполните все поля").open()
            return
        db = self.manager.app.db
        uid = db.create_user(name, email, password)
        if uid:
            MsgPopup(title="Готово", message="Пользователь создан. Войдите.").open()
            self.manager.current = "login"
        else:
            MsgPopup(title="Ошибка", message="Пользователь с таким email уже существует").open()


class HomeScreen(Screen):
    username_label = ObjectProperty(None)

    def on_enter(self):
        user = self.manager.app.current_user
        if user:
            self.username_label.text = f"Привет, {user.get('name')}!"
        else:
            self.username_label.text = "Привет, гость!"

    def logout(self):
        self.manager.app.current_user = None
        self.manager.current = "login"

    def manual_sync(self):
        threading.Thread(target=self.manager.app.sync_with_server, daemon=True).start()
        MsgPopup(title="Синхронизация", message="Запущена синхронизация в фоне").open()


class RoutesScreen(Screen):
    search_input = ObjectProperty(None)
    routes_box = ObjectProperty(None)

    def on_pre_enter(self):
        self.refresh_list()

    def refresh_list(self, query=None):
        self.routes_box.clear_widgets()
        app = self.manager.app
        if not app.current_user:
            return
        uid = app.current_user["id"]
        rows = app.db.list_routes(uid, query)
        for r in rows:
            rid, name, desc, lat, lon, created = r
            coord_text = f" ({lat:.2f}, {lon:.2f})" if lat and lon else ""
            display_text = f"{name}{coord_text}\\n{desc[:60]}" if desc else f"{name}{coord_text}"

            btn = Button(
                text=display_text,
                size_hint_y=None,
                height=dp(80),
                background_color=(0, 0, 0, 0),
                background_normal=''
            )

            btn.canvas.before.clear()
            with btn.canvas.before:
                Color(1, 1, 1, 1)
                RoundedRectangle(pos=btn.pos, size=btn.size, radius=[dp(15)])
                Color(0.9, 0.95, 1, 1)
                RoundedRectangle(pos=(btn.pos[0] + dp(1), btn.pos[1] + dp(1)),
                                 size=(btn.size[0] - dp(2), btn.size[1] - dp(2)),
                                 radius=[dp(14)])

            btn.bind(on_release=lambda inst, route_id=rid: self.open_detail(route_id))
            self.routes_box.add_widget(btn)

    def do_search(self):
        q = self.search_input.text.strip()
        self.refresh_list(query=q if q else None)

    def open_detail(self, route_id):
        rd = self.manager.get_screen("routedetail")
        rd.load_route(route_id)
        self.manager.current = "routedetail"


class NewRouteScreen(Screen):
    route_name_input = ObjectProperty(None)
    desc_input = ObjectProperty(None)
    lat_input = ObjectProperty(None)
    lon_input = ObjectProperty(None)

    def save_route(self):
        name = self.route_name_input.text.strip()
        desc = self.desc_input.text.strip()
        lat = self.lat_input.text.strip()
        lon = self.lon_input.text.strip()

        if not name:
            MsgPopup(title="Ошибка", message="Введите название маршрута").open()
            return

        latitude = float(lat) if lat else None
        longitude = float(lon) if lon else None

        app = self.manager.app
        uid = app.current_user["id"]
        rid = app.db.save_route(uid, name, desc, latitude, longitude)
        MsgPopup(title="Сохранено", message=f"Маршрут '{name}' сохранён").open()
        self.manager.current = "routes"

    def choose_on_map(self):
        self.manager.current = "map"


class RouteDetailScreen(Screen):
    route_name = ObjectProperty(None)
    route_desc = ObjectProperty(None)
    route_coords = ObjectProperty(None)
    _route = None

    def load_route(self, route_id):
        r = self.manager.app.db.get_route(route_id)
        if r:
            self._route = r
            rid, uid, name, desc, lat, lon, created = r
            self.route_name.text = name
            self.route_desc.text = f"{desc}\\n\\nСоздан: {created[:16].replace('T', ' ')}"

            if lat and lon:
                self.route_coords.text = f"Координаты: {lat:.4f}, {lon:.4f}"
            else:
                self.route_coords.text = "Координаты: не указаны"
        else:
            self.route_name.text = "Не найдено"
            self.route_desc.text = ""
            self.route_coords.text = "Координаты: не указаны"

    def add_favorite(self):
        app = self.manager.app
        uid = app.current_user["id"]
        if self.manager.app.db.add_favorite(uid, self._route[0]):
            MsgPopup(title="Добавлено", message="Маршрут добавлен в избранное").open()
        else:
            MsgPopup(title="ℹИнфо", message="Маршрут уже в избранном").open()

    def schedule_reminder(self):
        route_name = self._route[2] if self._route else "маршрут"
        msg = f"Напоминание: маршрут '{route_name}' — время отправляться!"

        def do_notify():
            if notification:
                notification.notify(title="TravelMate", message=msg)

        t = threading.Timer(60.0, do_notify)
        t.start()
        MsgPopup(title="Напоминание", message="Установлено через 1 минуту").open()

    def show_on_map(self):
        if not self._route:
            return

        rid, uid, name, desc, lat, lon, created = self._route
        if lat and lon:
            map_screen = self.manager.get_screen("map")
            map_screen.set_location(lat, lon, f"Маршрут: {name}")
            self.manager.current = "map"
        else:
            MsgPopup(title="Ошибка", message="Координаты не указаны для этого маршрута").open()

    def show_stats(self):
        app = self.manager.app
        if not app.current_user:
            return

        stats = app.db.get_user_stats(app.current_user["id"])
        message = f"Ваша статистика:\\n"
        message += f"• Маршрутов: {stats['route_count']}\\n"
        message += f"• В избранном: {stats['fav_count']}\\n"
        if stats['last_route']:
            message += f"• Последний: {stats['last_route'][0]}"

        MsgPopup(title="Статистика", message=message).open()


class FavoritesScreen(Screen):
    fav_box = ObjectProperty(None)

    def on_pre_enter(self):
        self.refresh()

    def refresh(self):
        self.fav_box.clear_widgets()
        app = self.manager.app
        if not app.current_user:
            return
        uid = app.current_user["id"]
        rows = app.db.list_favorites(uid)
        for r in rows:
            rid, name, desc, lat, lon = r
            coord_text = f" ({lat:.2f}, {lon:.2f})" if lat and lon else ""
            display_text = f"{name}{coord_text}\\n{desc[:60]}" if desc else f"{name}{coord_text}"

            btn = Button(
                text=display_text,
                size_hint_y=None,
                height=dp(60),
                background_color=(0, 0, 0, 0),
                background_normal=''
            )

            btn.canvas.before.clear()
            with btn.canvas.before:
                Color(1, 1, 1, 1)
                RoundedRectangle(pos=btn.pos, size=btn.size, radius=[dp(15)])
                Color(0.9, 0.95, 1, 1)
                RoundedRectangle(pos=(btn.pos[0] + dp(1), btn.pos[1] + dp(1)),
                                 size=(btn.size[0] - dp(2), btn.size[1] - dp(2)),
                                 radius=[dp(14)])

            btn.bind(on_release=lambda inst, route_id=rid: self.manager.get_screen("routedetail").load_route(
                route_id) or setattr(self.manager, "current", "routedetail"))
            self.fav_box.add_widget(btn)


class SettingsScreen(Screen):
    def sync_now(self):
        threading.Thread(target=self.manager.app.sync_with_server, daemon=True).start()
        MsgPopup(title="🔄 Синхронизация", message="Запущена синхронизация...").open()

    def show_stats(self):
        app = self.manager.app
        if not app.current_user:
            return

        stats = app.db.get_user_stats(app.current_user["id"])
        message = f"📊 Ваша статистика:\\n"
        message += f"• Всего маршрутов: {stats['route_count']}\\n"
        message += f"• В избранном: {stats['fav_count']}\\n"
        if stats['last_route']:
            message += f"• Последний маршрут: {stats['last_route'][0]}"

        MsgPopup(title="📊 Статистика", message=message).open()

    def clear_local(self):
        self.manager.app.db.clear_all()
        MsgPopup(title="🗑️ Очистка", message="Локальные данные удалены").open()


class TravelMateApp(App):
    current_user = None
    db = None
    sm = None

    def build(self):
        self.db = LocalDB()
        self.sm = Builder.load_string(KV)
        self.sm.app = self
        self._periodic_sync_thread = threading.Thread(target=self._periodic_sync_loop, daemon=True)
        self._periodic_sync_thread.start()
        return self.sm

    def on_start(self):
        cur = self.db.conn.cursor()
        cur.execute("SELECT id FROM users WHERE email=?", ("demo@travelmate.local",))
        if not cur.fetchone():
            self.db.create_user("Demo User", "demo@travelmate.local", "demo")

    def sync_with_server(self):
        if not self.current_user:
            return
        uid = self.current_user["id"]
        unsynced = self.db.get_unsynced_routes(uid)
        if not unsynced:
            return
        for r in unsynced:
            route_id, name, desc, lat, lon, created = r
            payload = {"user_id": uid, "name": name, "description": desc, "latitude": lat, "longitude": lon,
                       "created_at": created}
            try:
                url = f"{SERVER_URL}/routes"
                headers = {"Content-Type": "application/json"}
                resp = requests.post(url, json=payload, timeout=8)
                if resp.status_code in (200, 201):
                    self.db.mark_route_synced(route_id)
                else:
                    print("Sync failed for route", route_id, "status", resp.status_code)
            except Exception as e:
                print("Network error during sync:", e)
                break

    def _periodic_sync_loop(self):
        while True:
            try:
                if self.current_user:
                    self.sync_with_server()
            except Exception as e:
                print("Periodic sync error:", e)
            time.sleep(SYNC_INTERVAL_SECONDS)


if __name__ == "__main__":
    TravelMateApp().run()