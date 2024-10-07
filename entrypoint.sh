#!/bin/sh

# Exibir mensagens de log para monitoramento
echo "Verificando diretório de migrações..."

# Verificar se o diretório de migrações existe e criá-lo se necessário
if [ ! -d "/app/migrations" ]; then
    echo "Criando o diretório de migrações..."
    flask db init
else
    echo "Diretório de migrações já existe."
fi

# Executar o upgrade do banco de dados para aplicar as migrações
echo "Aplicando migrações ao banco de dados..."
flask db migrate
flask db upgrade

# Executar o comando passado como argumento para o entrypoint (iniciar o servidor Flask)
echo "Iniciando o servidor Flask..."
exec "$@"
