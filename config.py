import os
from dotenv import load_dotenv

load_dotenv()

TG_TOKEN = os.getenv('TG_TOKEN')
BINANCE_FIRST_KEY = os.getenv('BINANCE_FIRST_KEY')
BINANCE_SECOND_KEY = os.getenv('BINANCE_SECOND_KEY')
ALLOWED_USERS = os.getenv('MAIN_USER')
MAIN_USER = os.getenv('MAIN_USER')

START_PNL = 1.0  # задать PNL с которого начинает устанавливаться трэйлинг-стоп по умолчанию
GAP = 0.5         # задать отставание по умолчанию