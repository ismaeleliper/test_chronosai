# Test Chat AI Assistant
This project requires an assistant function at OpenAI Playground

### Function Assistant OpenAI
```
{
  "name": "get_address_by_cep",
  "description": "Busca o endereço completo com base no CEP fornecido.",
  "strict": false,
  "parameters": {
    "type": "object",
    "properties": {
      "cep": {
        "type": "string",
        "description": "O CEP para buscar o endereço, no formato 'XXXXX-XXX'."
      }
    },
    "required": [
      "cep"
    ]
  }
}
```
Clone the project:

And then set ID Assitant at .env you must add to your local dir



$`docker-compose up --build -d`

