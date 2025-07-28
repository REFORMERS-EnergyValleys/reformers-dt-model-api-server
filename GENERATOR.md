# OpenAPI Generator for Model API Server

Use [OpenAPI Generator](https://openapi-generator.tech/) for creating the server of the REFORMERS Model API, based on the dedicated [OpenAPI specification](https://github.com/REFORMERS-EnergyValleys/reformers-dt-model-api-specs).

## Installation

```
docker pull openapitools/openapi-generator-cli
```

## Generate server

Linux:
```
docker run --rm -v ${PWD}:/spec openapitools/openapi-generator-cli generate -g python-flask --package-name reformers_model_api_server -i /spec/openapi/bundled.yaml -o /spec/server
```

Windows:
```
docker run --rm -v %cd%:/spec openapitools/openapi-generator-cli generate -g python-flask --package-name reformers_model_api_server -i /spec/openapi/bundled.yaml -o /spec/server
```
