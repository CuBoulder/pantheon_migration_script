"""Migration Helper Functions."""
import os
import requests
from jinja2 import Environment, PackageLoader


def create_pantheon_site(auth_token, sid, path, instance_type, pantheon_size, user):
    """POST Request to create a new site on Pantheon."""
    site_payload = {
        'sid': sid,
        'path': path,
        'instance_type': instance_type,
        'pantheon_size': pantheon_size,
        'created_by': user,
    }

    request_headers = {'Authorization': auth_token}

    walnut_request = requests.post(
        'http://34.82.22.38/instance', headers=request_headers, json=site_payload)
    return walnut_request.status_code


def generate_simplesaml_config(subdomain, path):
    """Generate a the config file for simplesaml with hardcoded host values"""
    settings_variables = {"BASE_URL_PATH": f"https://{subdomain}.colorado.edu/{path}/simplesaml/", "SESSION_COOKIE_PATH": f"/{path}", "SESSION_COOKIE_DOMAIN": f"{subdomain}.colorado.edu"}
    jinja_env = Environment(loader=PackageLoader('migration_utils', 'templates'))
    template = jinja_env.get_template('config.php')
    render = template.render(settings_variables)

    # Remove the existing file.
    if os.access("config.php", os.F_OK):
        os.remove("config.php")
    # Write the render to a file.
    with open("config.php", "w") as open_file:
        open_file.write(render)
