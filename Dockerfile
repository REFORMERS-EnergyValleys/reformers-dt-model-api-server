FROM python:3.9-alpine

ENV PYTHONPATH=/app

RUN apk update && apk add git

# Install requirements from OpenAPI generator
COPY requirements.txt .
RUN pip install -r requirements.txt

# Install additional requirements.
RUN pip install waitress
RUN pip install git+https://github.com/REFORMERS-EnergyValleys/reformers-dt-model-repository-client.git
RUN pip install docker

COPY reformers_model_api_server /app/reformers_model_api_server

CMD ["waitress-serve", "--listen=*:80", "--call", "reformers_model_api_server.start_app:start_app_from_env"]
