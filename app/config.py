import os
from dotenv import load_dotenv

# Carregar as variáveis de ambiente do arquivo .env
load_dotenv()

class Config:
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    WEBHOOK_VERIFY_TOKEN=os.getenv('WEBHOOK_VERIFY_TOKEN')
    GRAPH_API_TOKEN=os.getenv('GRAPH_API_TOKEN')
    OPENAI_API_KEY=os.getenv('OPENAI_API_KEY')
    ASSISTANT_ID=os.getenv('ASSISTANT_ID')