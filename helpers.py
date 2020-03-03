"""Migration Helper Functions."""
import requests


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
        'http://127.0.0.1:5000/instance', headers=request_headers, json=site_payload)
    return walnut_request.status_code
