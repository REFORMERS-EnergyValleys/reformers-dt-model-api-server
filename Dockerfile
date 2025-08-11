FROM python:3.9-alpine

ENV PYTHONPATH=/app

# Install git & docker.
RUN apk update && apk add git docker

# Install requirements from OpenAPI generator.
COPY requirements.txt .
RUN pip install -r requirements.txt

# Install additional requirements.
RUN pip install docker
RUN pip install waitress
RUN pip install git+https://github.com/REFORMERS-EnergyValleys/reformers-dt-model-repository-client.git
RUN pip install ansistrip

COPY reformers_model_api_server /app/reformers_model_api_server

CMD ["waitress-serve", "--listen=*:80", "--url-prefix=api", "--call", "reformers_model_api_server.start_app:start_app_from_env"]
