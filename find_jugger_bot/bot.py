import json, os, re
from math import radians, degrees, sin, cos, asin, acos, sqrt
import discord

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import googlemaps

with open('keys.json') as f:
    secret_data = json.load(f)
bot_token = secret_data['bot_token']
google_token = secret_data['google_dev'] #'google_API'

bot_url = 'https://discord.com/api/oauth2/authorize?client_id=1137642796937908244&permissions=2048&scope=bot'

class FindJuggerClient(discord.Client):
    spreadsheet = None

    def is_asking_where(self, message):
        message = message.lower()
        if message.endswith('?'):
            if 'jugger' in message:
                return True
        return False
    
    nasty_regex = re.compile('(near|close to|around|in)\s([a-zA-Z\s,]+)')
    def where_asked_about(self, message):
        where = self.nasty_regex.search(message)
        if where is None:
            return '?'
        return where.group(2)
    
    gmaps = googlemaps.Client(key=google_token)
    def find_nearest_jugger(self, locationstring):
        geocode_result = self.gmaps.geocode(locationstring)
        if len(geocode_result) > 0:
            geocode_latlong = geocode_result[0]['geometry']['location']
            lat = geocode_latlong['lat']
            long = geocode_latlong['lng']
            return self.closest_club_from_db(lat, long)
        return "Unfortunately, I can't figure out where that is."
    
    def spin_up_spreadsheet(self):
        if self.spreadsheet:
            return
        # If modifying these scopes, delete the file token.json.
        SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']

        club_data_spreadsheet_id = '1KHNrKrpunvWNaGVStFhj7Ra2EC_kgK8sZQsxa2yiJuk'
        club_data_range = 'Club List!A2:O'

        creds = None
        # The file token.json stores the user's access and refresh tokens, and is
        # created automatically when the authorization flow completes for the first
        # time.
        if os.path.exists('token.json'):
            creds = Credentials.from_authorized_user_file('token.json', SCOPES)
        # If there are no (valid) credentials available, let the user log in.
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    'credentials.json', SCOPES)
                creds = flow.run_local_server(port=0)
            # Save the credentials for the next run
            with open('token.json', 'w+') as token:
                token.write(creds.to_json())

        try:
            service = build('sheets', 'v4', credentials=creds)

            # Call the Sheets API
            sheet = service.spreadsheets()
            result = sheet.values().get(spreadsheetId=club_data_spreadsheet_id,
                                        range=club_data_range).execute()
            values = result.get('values', [])

            if not values:
                print('Error accessing club information??')
                return

            self.spreadsheet = values
        except HttpError as err:
            print(err)
    
    # from @petehuston on medium (but it's actually just math)
    def great_circle(self, lon1, lat1, lon2, lat2):
        lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
        return 6371 * (
            acos(sin(lat1) * sin(lat2) + cos(lat1) * cos(lat2) * cos(lon1 - lon2))
        )
    
    def closest_club_from_db(self, lat, long):
        self.spin_up_spreadsheet()
        closest_distance = 999999999
        closest_club = None
        NAME = 0
        CITY = 1
        COUNTRY = 2
        WEBSITE = 3
        PERSON = 4
        METHOD = 5
        ACTIVE = 6
        ARMORED = 7
        YOUTH = 8
        LAT = 9
        LONG = 10 # I hate this
        for idx, club in enumerate(self.spreadsheet):
            if club[ACTIVE] == 'FALSE' or club[ARMORED] == 'TRUE' or club[YOUTH] == 'TRUE':
                continue
            distance = self.great_circle(float(club[LAT]), float(club[LONG]), lat, long)
            if distance < closest_distance:
                closest_distance = distance
                closest_club = idx
        closest = self.spreadsheet[closest_club]
        return f"The closest active club we know of is {closest[NAME]} in {closest[CITY]} ({closest_distance:.1f} km away). You can reach them through {closest[WEBSITE]}, {closest[PERSON]}, {closest[METHOD]}."

    async def on_ready(self):
        print(f'Logged in as {self.user} (ID: {self.user.id})')
        print('------')
        self.spin_up_spreadsheet()

    async def on_message(self, message):
        # we do not want the bot to reply to itself
        if message.author.id == self.user.id:
            return
        
        # this is a basic try at a formula for a question about where jugger is
        if self.is_asking_where(message.content):
            where_asked_about = self.where_asked_about(message.content)
            if where_asked_about != '?':
                await message.reply(f"Hello! I think you're asking for jugger clubs near {where_asked_about}. {self.find_nearest_jugger(where_asked_about)} I am just a bot, though. Maybe you can find something better at https://juggercouncil.org/en/map", mention_author=True)
            else:
                await message.reply('Sorry, I am not a very smart bot. Try asking like "is there jugger near Copenhagen?" or have a look at https://juggercouncil.org/en/map', mention_author=True)


intents = discord.Intents.default()
intents.message_content = True

client = FindJuggerClient(intents=intents)
client.run(bot_token)