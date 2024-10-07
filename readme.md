# Test Chat AI Assistant

run: `docker-compose up --build -d`

### Function Assistant Open ai
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