import json
import time
import openai
import requests
from flask import request, jsonify, current_app as app
from .models import Thread
from app.app import db

ZAPI_PHONE_ID = app.config['ZAPI_PHONE_ID']
ZAPI_API_TOKEN = app.config['ZAPI_API_TOKEN']
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

    max_attempts = 10
    attempts = 0
    while attempts < max_attempts:
        time.sleep(5)
        attempts += 1
        run_status = client.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run.id)

        content_array = []
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

        elif run_status.status == 'requires_action':
            required_actions = run_status.required_action.submit_tool_outputs.model_dump()
            tool_outputs = []

            for action in required_actions["tool_calls"]:
                func_name = action['function']['name']
                arguments = json.loads(action['function']['arguments'])

                if func_name == "get_address_by_cep":
                    cep = arguments.get('cep', '01001-000')
                    output = get_address_by_cep(cep)
                    tool_outputs.append({
                        "tool_call_id": action['id'],
                        "output": output
                    })
                else:
                    return default_message

            client.beta.threads.runs.submit_tool_outputs(
                thread_id=thread_id,
                run_id=run.id,
                tool_outputs=tool_outputs
            )
        else:
            time.sleep(3)

    return default_message


# Rota para processar o webhook de mensagens do WhatsApp
@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()
    print("Dados recebidos no webhook:", data)

    # Verificar se a estrutura do payload está correta
    if data and data.get("type") == "ReceivedCallback":
        # Adicionar verificação para ignorar mensagens enviadas pelo próprio bot
        if data.get("fromMe"):
            print("Mensagem enviada pelo bot. Ignorando para evitar loop.")
            return jsonify({"status": "ignored", "message": "Mensagem enviada pelo próprio bot. Ignorada."}), 200

        phone_number = data.get("phone")  # Número de telefone do remetente
        text = data.get("text", {}).get("message", "")  # Conteúdo da mensagem enviada pelo usuário

        if not phone_number or not text:
            return jsonify({"status": "error", "message": "Dados de telefone ou mensagem ausentes"}), 400

        print(f"Mensagem recebida de {phone_number}: {text}")

        # Responder automaticamente à mensagem recebida
        message_assistant = assistant(message=text, phone=phone_number + "123", user="Prezado")

        # Enviar resposta de volta ao remetente usando a API Z-API
        send_url = f"https://api.z-api.io/instances/{ZAPI_PHONE_ID}/token/{ZAPI_API_TOKEN}/send-text"
        payload = {
            "phone": phone_number,
            "message": message_assistant
        }

        response = requests.post(send_url, json=payload)

        if response.status_code == 200:
            print("Mensagem de resposta enviada com sucesso.")
            return jsonify({"status": "success", "message": "Mensagem recebida e respondida!"}), 200
        else:
            print("Falha ao enviar a mensagem de resposta:", response.text)
            return jsonify({"status": "error", "message": response.text}), response.status_code
    else:
        return jsonify({"status": "error", "message": "Estrutura de dados recebida é inválida"}), 400


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
