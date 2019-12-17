# Web Express Migration Script

A python 3 script to automate moving sites from our webservers to Pantheon

## Pre-requisites

You will need to have the following items ready before using the script:

- [CU Boulder Pantheon Organization Access](https://dashboard.pantheon.io/login). You will need:
  - Organization ID (dashes included)
  - Express Mono Upstream ID (dashes included)

- [Terminus](https://pantheon.io/docs/terminus/) - Terminus, provides advanced interaction with Pantheon. Terminus enables you to do almost everything in a terminal that you can do in the Dashboard, and much more. [Installation steps](https://pantheon.io/docs/terminus/install/). Make sure to follow the both the Install and Authenticate: Machine Token steps.

- Add your ssh key to the utility servers
  ```
    ssh-copy-id YOUR_IDENTIKEY@remote-host
  ```

- A directory named `cert` in the same directory as this project with a pair of private and public keys used for simplesamlphp

## Running the Script

1. Add run `ssh-add` in the same directory as the `migration.sh` script
2. Replace variables `identikey`, `user_password`, `org`, and `upstream_id` accordingly in `local_vars.py`
3. Add the list of sites to migrate to `instance_list.txt` in the format `instance_id,subdomain` (one pair per line)
4. Run script simply with `python3 python_migration_script.py`

A logging file will be created: `app.log`