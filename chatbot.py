import json
import requests
import time
import urllib

TOKEN = "TELEGRAM API KEY"
OWM_KEY = "OPENWHEATHERMAP API KEY"
# Lambda functions to parse updates from Telegram
def getText(update):
    return update["message"]["text"]
def getLocation(update):
    return update["message"]["location"]
def getChatId(update):
    return update["message"]["chat"]["id"]
def getUpId(update):
    return int(update["update_id"])
def getResult(updates):
    return updates["result"]

# Lambda functions to parse weather responses
def getDesc(w):
    return w["weather"][0]["description"]
def getTemp(w):
    return w["main"]["temp"]
def getCity(w):
    return w["name"]

# Cities for weather requests
cities = ["London", "Paris", "Rabat"]

def parseConfig():
    global URL, URL_OWM
    URL = "https://api.telegram.org/bot{}/".format(TOKEN)
    URL_OWM = "http://api.openweathermap.org/data/2.5/weather?appid={}&units=metric".format(OWM_KEY)

# Make a request to Telegram bot and get JSON response
def makeRequest(url):
    r = requests.get(url)
    resp = json.loads(r.content.decode("utf8"))
    return resp

# Return all the updates with ID > offset
def getUpdates(offset=None):
    url = URL + "getUpdates?timeout=%s"
    if offset:
        url += "&offset={}".format(offset)
    js = makeRequest(url)
    return js

# Build a one-time keyboard for on-screen options
def buildKeyboard(items):
    keyboard = [[{"text": item}] for item in items]
    replyKeyboard = {"keyboard": keyboard, "one_time_keyboard": True}
    return json.dumps(replyKeyboard)

def buildCitiesKeyboard():
    keyboard = [[{"text": c}] for c in cities]
    keyboard.append([{"text": "Share location", "request_location": True}])
    replyKeyboard = {"keyboard": keyboard, "one_time_keyboard": True}
    return json.dumps(replyKeyboard)

# Query OWM for the weather for place or coords
def getWeather(place):
    if isinstance(place, dict):     # coordinates provided
        lat, lon = place["latitude"], place["longitude"]
        url = URL_OWM + "&lat=%f&lon=%f&cnt=1" % (lat, lon)
        js = makeRequest(url)
        return u"%s \N{DEGREE SIGN}C, %s in %s" % (getTemp(js), getDesc(js), getCity(js))
    else:                           # place name provided
        # make req
        url = URL_OWM + "&q={}".format(place)
        js = makeRequest(url)
        return u"%s \N{DEGREE SIGN}C, %s in %s" % (getTemp(js), getDesc(js), getCity(js))

# Send URL-encoded message to chat id
def sendMessage(text, chatId, interface=None):
    text = text.encode('utf-8', 'strict')
    text = urllib.parse.quote_plus(text)
    url = URL + "sendMessage?text={}&chat_id={}&parse_mode=Markdown".format(text, chatId)
    if interface:
        url += "&reply_markup={}".format(interface)
    requests.get(url)

# Get the ID of the last available update
def getLastUpdateId(updates):
    ids = []
    for update in getResult(updates):
        ids.append(getUpId(update))
    return max(ids)

# Keep track of conversation states: 'weatherReq'
chats = {}

# Echo all messages back
def handleUpdates(updates):
    for update in getResult(updates):
        chatId = getChatId(update)
        try:
            text = getText(update)
        except Exception as e:
            loc = getLocation(update)
            # Was weather previously requested?
            if (chatId in chats) and (chats[chatId] == "weatherReq"):
                # Send weather to chat id and clear state
                sendMessage(getWeather(loc), chatId)
                del chats[chatId]
            continue

        if text == "/weather":
            keyboard = buildCitiesKeyboard()
            chats[chatId] = "weatherReq"
            sendMessage("Select a city", chatId, keyboard)
        elif text == "/start":
            sendMessage("Hi, I'm your WeatherBot. \nType: /weather.", chatId)
        elif text.startswith("/"):
            continue
        elif (text in cities) and (chatId in chats) and (chats[chatId] == "weatherReq"):
            # Send weather to chat id and clear state
            sendMessage(getWeather(text), chatId)
            del chats[chatId]
        else:
            keyboard = buildKeyboard(["/weather"])
            sendMessage("I learn new things every day but for now you can ask me about the weather.", chatId, keyboard)


def main():
    # Get tokens and keys
    parseConfig()
    # Main loop
    last_update_id = None
    while True:
        updates = getUpdates(last_update_id)
        if len(getResult(updates)) > 0:
            last_update_id = getLastUpdateId(updates) + 1
            handleUpdates(updates)
        time.sleep(0.5)


if __name__ == "__main__":
    main()