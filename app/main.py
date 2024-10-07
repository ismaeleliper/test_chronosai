import json
import time
import openai
import requests
from flask import request, jsonify, current_app as app
from .models import Thread
from app.app import db

WEBHOOK_VERIFY_TOKEN = app.config['WEBHOOK_VERIFY_TOKEN']
GRAPH_API_TOKEN = app.config['GRAPH_API_TOKEN']
OPENAI_API_KEY = app.config['OPENAI_API_KEY']

assistant_id = app.config['ASSISTANT_ID']

# Inicializa o cliente OpenAI
client = openai.OpenAI(api_key=OPENAI_API_KEY)


# Função para obter o endereço a partir do CEP usando a API ViaCEP
def get_address_by_cep(cep: str) -> str:
    url = f"https://viacep.com.br/ws/{cep}/json/"
    response = requests.get(url)

    if response.status_code == 200:
        data = response.json()
        if "erro" not in data:
            # Formatar o endereço com base no retorno da API
            address = f"{data['logradouro']}, {data['bairro']}, {data['localidade']} - {data['uf']}"
            return address
        else:
            return "CEP inválido ou não encontrado."
    else:
        return "Erro ao conectar com a API ViaCEP."


def assistant(phone, message, user):

    thread_id = None
    default_message = "Desculpa, não consegui entender a última mensagem 😅. Você pode tentar de novo, por favor?"

    # Tente encontrar um Thread existente pelo telefone
    existing_thread = Thread.query.filter_by(phone=phone).first()

    if existing_thread:
        thread_id = existing_thread.thread_id
    else:
        # Cria um novo Thread se não existir
        thread = client.beta.threads.create()
        new_thread = Thread(thread_id=thread.id, phone=phone)
        db.session.add(new_thread)
        db.session.commit()
        thread_id = new_thread.thread_id

    # Adiciona uma mensagem ao Thread
    client.beta.threads.messages.create(
        thread_id=thread_id,
        role="user",
        content=message
    )

    # Executa o assistente com instruções específicas
    run = client.beta.threads.runs.create(
        thread_id=thread_id,
        assistant_id=assistant_id,
        instructions="Please address the user as " + user + "."
    )

    # Monitorar o estado do processo com um máximo de 10 tentativas
    max_attempts = 10
    attempts = 0
    while attempts < max_attempts:
        time.sleep(5)
        attempts += 1
        # Obtém o status do run
        run_status = client.beta.threads.runs.retrieve(
            thread_id=thread_id,
            run_id=run.id
        )

        content_array = []
        # Se a execução estiver completa, recupera as mensagens
        if run_status.status == 'completed':
            messages = client.beta.threads.messages.list(thread_id=thread_id)
            for msg in messages.data:
                role = msg.role
                content = msg.content[0].text.value
                if role.capitalize() == "Assistant":
                    content_array.append(content)

            if content_array:
                return content_array[0]
            
            return default_message

        # Se precisar de ação, processa as chamadas de função
        elif run_status.status == 'requires_action':
            required_actions = run_status.required_action.submit_tool_outputs.model_dump()
            tool_outputs = []

            for action in required_actions["tool_calls"]:
                func_name = action['function']['name']
                
                # Convertendo a string de argumentos para dicionário
                arguments = json.loads(action['function']['arguments'])

                # Identifica a função e executa a ação correspondente
                if func_name == "get_address_by_cep":
                    cep = arguments.get('cep', '01001-000')
                    output = get_address_by_cep(cep)
                    tool_outputs.append({
                        "tool_call_id": action['id'],
                        "output": output
                    })
                else:
                    return default_message

            print("Submitting tool outputs to the Assistant...")
            client.beta.threads.runs.submit_tool_outputs(
                thread_id=thread_id,
                run_id=run.id,
                tool_outputs=tool_outputs
            )
        else:
            print("Waiting for the Assistant to process...")
            time.sleep(3)

    return default_message


# Variável para armazenar IDs de mensagens processadas
processed_message_ids = set()

# Função para evitar duplicação de mensagens
def is_message_processed(message_id):
    if message_id in processed_message_ids:
        return True
    processed_message_ids.add(message_id)
    return False


# Função que processa a mensagem usando a API do WhatsApp e OpenAI
def process_message(message, business_phone_number_id, contact_name):
    reply_url = f"https://graph.facebook.com/v18.0/{business_phone_number_id}/messages"
    headers = {
        "Authorization": f"Bearer {GRAPH_API_TOKEN}",
        "Content-Type": "application/json"
    }

    # Mensagem do usuário
    user_input = message["text"]["body"]
    message_assistant = assistant(message=user_input, phone=business_phone_number_id + "12", user=contact_name)

    # Mensagem de resposta personalizada usando o nome do contato
    response_message = message_assistant

    data = {
        "messaging_product": "whatsapp",
        "to": message["from"],
        "text": {"body": response_message},
        "context": {
            "message_id": message["id"]
        }
    }

    # Enviar a resposta
    response = requests.post(reply_url, headers=headers, json=data)
    if response.status_code != 200:
        print(f"Failed to send message: {response.status_code}, {response.text}")


# Rota para processar o webhook de mensagens do WhatsApp
@app.route("/webhook", methods=["POST"])
def webhook():
    # Extração segura dos dados recebidos no webhook
    entry = request.json.get('entry', [{}])[0]
    changes = entry.get('changes', [{}])[0]
    value = changes.get('value', {})
    message = value.get('messages', [{}])[0]

    # Obter o nome do contato, se disponível
    contacts = value.get('contacts', [{}])[0]
    contact_name = contacts.get('profile', {}).get('name', 'Prezado')

    # Verificar se a mensagem recebida é de texto e se já foi processada
    if "id" in message:
        message_id = message["id"]
        if is_message_processed(message_id):
            print(f"Mensagem {message_id} já processada. Ignorando.")
            return jsonify({"status": "duplicated_message_ignored"}), 200
    else:
        print("ID da mensagem não encontrado.")
        return jsonify({"status": "error", "message": "Message ID not found"}), 400

    # Verificar se a mensagem recebida é de texto
    if message.get("type") == "text":
        business_phone_number_id = value.get('metadata', {}).get('phone_number_id')
        process_message(message, business_phone_number_id, contact_name)

    return jsonify({"status": "success"}), 200


@app.route("/webhook", methods=["GET"])
def verify_webhook():
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")

    # Verificar se o token e o modo são válidos
    if mode == "subscribe" and token == WEBHOOK_VERIFY_TOKEN:
        print("Webhook verified successfully!")
        return challenge, 200
    else:
        return "Forbidden", 403
