import sys
from utils.text_bot_client import TextBotClient

TOKEN = sys.argv[1]
CHANNEL = sys.argv[2]

client = TextBotClient(CHANNEL)
client.run(TOKEN)

# python text-bot.py TOKEN CHANNEL