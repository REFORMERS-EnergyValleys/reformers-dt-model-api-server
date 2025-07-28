# TODOS Model API

+ Naming / implementation conventions:
  - generator images + versions
  - model images + versions
  - model artifacts (group ID, etc.) + versions
  - labels / parameters (mandatory, optional)
    - images
    - artifacts

+ OpenAPI:
  - get specific model info
  - model -> 404 not found
  - models -> images + artifacts
  - generator / model image names with "namespace prefix", e.g., "/reformers/test1/generator1/v2/model3:v4"
+ server API:
  - reformers_model_repo_client -> ApiException vs. Exception
+ generators:
  - info: link to CI/CD job
