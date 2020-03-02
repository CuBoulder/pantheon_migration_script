# Web Express Migration Script

A python 3 script to automate moving sites from our webservers to Pantheon

## Pre-requisites

You will need to have the following items ready before using the script:

- Python 3.7 or above installed
  - python `requests` library

    ```bash
    python3 -m pip install requests
    ```

- MySQL 5.7 or above installed

- [CU Boulder Pantheon Organization Access](https://dashboard.pantheon.io/login).
  - Organization ID (dashes included)
  - Express Mono Upstream ID (dashes included)

- [Install Composer](https://tecadmin.net/install-composer-on-macos/)

- [Terminus](https://pantheon.io/docs/terminus/install/) - Make sure to follow the both the Install and Authenticate: Machine Token steps.

- [Terminus Rsync Plugin](https://github.com/pantheon-systems/terminus-rsync-plugin) (composer needed)

- [Terminus Secrets Plugin](https://github.com/pantheon-systems/terminus-secrets-plugin)

- Add your ssh key to the utility servers, it will like something like:
  
  ```bash
    ssh-copy-id [IDENTIKEY]@osr-[ENV]-util01.int.colorado.edu
  ```

- [Add your SSH key to Pantheon](https://pantheon.io/docs/ssh-keys#add-your-ssh-key-to-pantheon)
  
- A directory named `cert` in the same directory as this project with a pair of private and public keys used for simplesamlphp
  
- A `secrets.json` file in the same directory as this project

## Running the Script

1. Run the command `ssh-add` in the same directory as the `python_migration_script.py` file (if your SSH key has a passphrase)
2. Replace variables `IDENTIKEY`, `USER_PASSWORD`, `ORG`, `UPSTREAM_ID`, `WALNUT_TOKEN`, and `WALNUT_USER` accordingly in `local_vars.py`
3. Add the list of sites to migrate to `instance_list.txt` in the format `instance_id,subdomain` (one pair per line)
4. Run script simply with `python3 python_migration_script.py`

A logging file will be created: `app.log`
