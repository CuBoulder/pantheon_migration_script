import subprocess
import os

def pantheon_secrets(pantheon_site_name):

    # pantheon_site_name = "jesus-sandbox"

    subprocess.Popen([f"cp {pantheon_site_name}/sites/default/default.settings.php {pantheon_site_name}/sites/default/settings.php"], shell=True)

    # Make cert directories
    subprocess.Popen(
        [f"mkdir -p {pantheon_site_name}/private/simplesamlphp-1.17.2/cert/"], shell=True)
    subprocess.Popen(
        [f"mkdir -p {pantheon_site_name}/sites/default/files/private/cert"], shell=True)
    print("made private cert dir")

    # Make copy certs
    subprocess.Popen(
        [f"cp cert/saml.crt {pantheon_site_name}/sites/default/files/private/cert/saml.crt"], shell=True)
    subprocess.Popen(
        [f"cp cert/saml.pem {pantheon_site_name}/sites/default/files/private/cert/saml.pem"], shell=True)

    # Symlinks
    subprocess.Popen(
        [f"ln -s {pantheon_site_name}/sites/default/files/private/cert/saml.crt {pantheon_site_name}/private/simplesamlphp-1.17.2/cert/saml.crt"], shell=True)
    subprocess.Popen(
        [f"ln -s {pantheon_site_name}/sites/default/files/private/cert/saml.pem {pantheon_site_name}/private/simplesamlphp-1.17.2/cert/saml.pem"], shell=True)

    print("done")
