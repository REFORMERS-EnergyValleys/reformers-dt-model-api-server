#!/usr/bin/env python3
from .start_app import start_app
import click

class PrefixMiddleware:

    def __init__(self, app, prefix):
        self.app = app
        self.prefix = prefix

    def __call__(self, environ, start_response):
        environ['PATH_INFO'] = environ['PATH_INFO'][len(self.prefix):]
        environ['SCRIPT_NAME'] = self.prefix
        return self.app(environ, start_response)

@click.command()
@click.option('-s', '--specification', default='openapi.yaml', help='OpenAPI specification file name (relative to subfolder \'openapi\')')
@click.option('-h', '--host', default='reformers-dev.ait.ac.at', help='URL to repository')
@click.option('--repo-auth-config', default='repo-auth-config.json', help='path to authentication config file for accessing the repository')
@click.option('--registry-auth-config', default='registry-auth-config.json', help='path to authentication config file for accessing the container registries')
@click.option('--metagenerator-auth-config', default='registry-auth-config.json', help='path to authentication config file for accessing the container registries passed as input to metagenerators')
@click.option('--remove-containers', default=True, help='set this to false to remove containers after they have exited')
@click.option('--verify-ssl', default=False, help='set this to true to verify SSL certificates')
def main(specification, host, repo_auth_config, registry_auth_config, metagenerator_auth_config, remove_containers, verify_ssl):
    flask_app = start_app(specification, host, repo_auth_config, registry_auth_config, metagenerator_auth_config, remove_containers, verify_ssl)
    flask_app.app.wsgi_app = PrefixMiddleware(flask_app.app.wsgi_app, prefix='/api')
    flask_app.run(port=8080)

if __name__ == '__main__':
    main()
