#!/usr/bin/env python3
from .start_app import start_app
import click

@click.command()
@click.option('-s', '--specification', default='openapi.yaml', help='OpenAPI specification file name (relative to subfolder \'openapi\')')
@click.option('-h', '--host', default='reformers-dev.ait.ac.at', help='URL to repository')
@click.option('--registry-auth-config', default='auth-config.json', help='path to authentication config file for accessing the container registries')
@click.option('--repo-auth-config', default='auth-config.json', help='path to authentication config file for accessing the repository')
@click.option('--remove-containers', default=True, help='set this to false to remove containers after they have exited')
@click.option('--verify-ssl', default=False, help='set this to true to verify SSL certificates')
def main(specification, host, registry_auth_config, repo_auth_config, remove_containers, verify_ssl):
    flask_app = start_app(specification, host, registry_auth_config, repo_auth_config, remove_containers, verify_ssl)
    flask_app.run(port=8080)

if __name__ == '__main__':
    main()
