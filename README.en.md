# Binance trailing-stop bot
## Изменить язык: [Русский](README.md)
***
Telegram bot for private use, sets trailing-stop to absolute values for futures trading on Binance.
## Functionality:
1. Sets a trailing stop in absolute value (in USDT) with a specified gap when the pair reaches a specified profit (in USDT)
2. Allows you to change the backlog and profit from which the trailing stop is set
3. Sends a notification when a stop order is triggered
4. Displays the result of the transaction
5. Allows you to track the total number of positions opened in short / long, the total margin on positions
## Commands:
**For convenience, it is recommended to add these commands to the side menu of the bot using [BotFather](https://t.me/BotFather).**
- /pnl X - sets the PNL value from which the trailing stop is opened, where X is the PNL value in USDT;
- /gap N - sets trailing stop gap, where N - gap value in USDT;
- /settings - displays current PNL and USDT backlog settings;
- /monitor - starts the algorithm;
- /stop - stops the algorithm;
- /status - reports the status of the algorithm;
- /info - informs about the number of positions opened in short, long, as well as about the margin;
- /help - provides command options.
## Installation and use:
- Create an .env file containing the following variables:
> the file is created in the root folder of the project
   - specify the bot's telegram token and Binance keys (with access to futures trading) in the file:\
   **TG_TOKEN**=TOKEN\
   **BINANCE_FIRST_KEY**=KEY_1\
   **BINANCE_SECOND_KEY**=KEY_2
   - **MAIN_USER** contains the ID of the user who has access to execute commands and receives notifications. (for example: MAIN_USER=1234)
> To determine the user ID, you need to send any message from the corresponding account to the next [bot] (https://t.me/getmyid_bot). Value contained in **Your user ID** - User ID
- Install the virtual environment and activate it (if necessary):
> Installation and activation in the root folder of the project
```sh
python3 -m venv venv
source venv/bin/activate # for macOS
source venv/Scripts/activate # for Windows
```
- Install dependencies:
```sh
pip install -r requirements.txt
```
- Run project:
```sh
python3 main.py
```