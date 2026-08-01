import os
from dotenv import load_dotenv

load_dotenv()

POSTMAN_KEY = os.environ.get('POSTMAN_API_KEY')