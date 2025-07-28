#!/usr/bin/env python3
from .start_app import start_app
import click

@click.command()
@click.option('-s', '--specification', default='openapi.yaml', help='OpenAPI specification file name')
@click.option('-h', '--host', default='reformers-dev.ait.ac.at', help='URL to repository')
@click.option('-a', '--auth-config', default='auth-config.json', help='path to authentication config file')
@click.option('--remove-containers', default=True, help='set this to false to remove containers after they have exited')
@click.option('--verify-ssl', default=False, help='set this to false to skip verifying SSL certificates')
def main(specification, host, auth_config, remove_containers, verify_ssl):
    flask_app = start_app(specification, host, auth_config, remove_containers, verify_ssl)
    flask_app.run(port=8080)

if __name__ == '__main__':
    main()
