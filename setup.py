import sys
from setuptools import setup, find_packages

NAME = "reformers_model_api_server"
VERSION = "1.0.0"

# To install the library, run the following
#
# python setup.py install
#
# prerequisite: setuptools
# http://pypi.python.org/pypi/setuptools

REQUIRES = [
    "connexion>=2.0.2",
    "swagger-ui-bundle>=0.0.2",
    "python_dateutil>=2.6.0"
]

setup(
    name=NAME,
    version=VERSION,
    description="REFORMERS Digital Twin: Model API",
    author_email="",
    url="",
    keywords=["OpenAPI", "REFORMERS Digital Twin: Model API"],
    install_requires=REQUIRES,
    packages=find_packages(),
    package_data={'': ['openapi/openapi.yaml']},
    include_package_data=True,
    entry_points={
        'console_scripts': ['reformers_model_api_server=reformers_model_api_server.__main__:main']},
    long_description="""\
    This API provides the model creation and validation capabilities of the digital twin. A family of models, which can be data or equation-based, is created in an automated way by the digital twin. The models differ in resolution and computational complexity, spanning different energy vectors (heat, electricity, gas) and having different time and component details. The models are calibrated to real-world data. These models are used by different digital twin services  _Funding acknowledgement_: The [REFORMERS project](https://reformers-energyvalleys.eu) has received funding from the European Union’s research and innovation programme Horizon Europe under the [Grant Agreement No.101136211](https://cordis.europa.eu/project/id/101136211) 
    """
)

