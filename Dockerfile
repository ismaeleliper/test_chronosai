# Use uma imagem base oficial do Python
FROM python:3.9-slim

# Definir diretório de trabalho dentro do container
WORKDIR /app

# Copiar o arquivo de requisitos para o diretório de trabalho
COPY requirements.txt requirements.txt

# Instalar as dependências do Flask e outras bibliotecas
RUN pip install --no-cache-dir -r requirements.txt

# Copiar todo o conteúdo do diretório local para o diretório de trabalho no container
COPY app/ .

# Expor a porta que o Flask usará dentro do container
EXPOSE 5000

# Definir a variável de ambiente para que o Flask possa rodar
ENV FLASK_APP=/app/app.py

# Adicionar um script de inicialização para aplicar migrações
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Definir o ponto de entrada para o script
ENTRYPOINT ["/entrypoint.sh"]

# Comando padrão para iniciar o Flask
CMD ["flask", "run", "--host=0.0.0.0"]
