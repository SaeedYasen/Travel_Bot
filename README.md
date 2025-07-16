# Travel Bot

## The Team

-  Yara
-  Raz
-  Saeed

## About this bot

Our travel bot helps you find your next adventure in Israel – one trip at a time! 🗺️ Just tell it where you'd like to travel (north, center, or south), and it will start suggesting trips nearby. For each suggestion, you can like or dislike. Like it? You'll get a detailed description powered by Gemini AI also the current weather using API. Don’t like it? The bot will skip to the next. All your favorite trips are saved in your history for easy access later!

https://t.me/trip_master_devs_bot

<img width="450" height="747" alt="image" src="https://github.com/user-attachments/assets/d0011864-934c-4490-a863-09aa9be9356a" />
<img width="450" height="511" alt="image" src="https://github.com/user-attachments/assets/26690849-59ff-46d0-b32b-c6ff37ce9951" />
<img width="450" height="177" alt="image" src="https://github.com/user-attachments/assets/993a7fb9-f081-49a5-aff0-d365bc86a563" />

## Instructions for Developers

### Prerequisites

- [uv](https://docs.astral.sh/uv/getting-started/installation/) (uv will also install Python for you!)

### Setup

- git clone this repository
- cd into the project directory
- Get an API Token for a bot via the [BotFather](https://telegram.me/BotFather)
- Create a `bot_secretes.py` file with your bot token:

      TOKEN = 'xxxxxxx'
      API_WHETHER ='xxxxxxx'
      GEMINI_API_KEY = 'xxxxx'

### Running the bot

- Run the bot (This will also install Python 3.13 and all dependencies):

      uv run bot.py
