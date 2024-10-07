import os
from dotenv import load_dotenv

# Carregar as variáveis de ambiente do arquivo .env
load_dotenv()

class Config:
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    ZAPI_PHONE_ID=os.getenv('ZAPI_PHONE_ID')
    ZAPI_API_TOKEN=os.getenv('ZAPI_API_TOKEN')
    OPENAI_API_KEY=os.getenv('OPENAI_API_KEY')
    ASSISTANT_ID=os.getenv('ASSISTANT_ID')