# Web Express Migration Script

A bash script to automate moving sites from our webservers to Pantheon

## Pre-requisites

You will need to have the following items ready before using the script:

- [CU Boulder Pantheon Organization Access](https://dashboard.pantheon.io/login). You will need:
  - Organization ID
  - Express Mono Upstream ID

- [jq](https://stedolan.github.io/jq/) - jq is a lightweight and flexible command-line JSON processor
  
  ```bash
  brew install jq
  ```

- [Terminus](https://pantheon.io/docs/terminus/) - Terminus, provides advanced interaction with Pantheon. Terminus enables you to do almost everything in a terminal that you can do in the Dashboard, and much more. [Installation steps](https://pantheon.io/docs/terminus/install/). Make sure to follow the both the Install and Authenticate: Machine Token steps.

- Add your ssh key to the utility servers
  ```
    ssh-copy-id YOUR_IDENTIKEY@remote-host
  ```
  
- Create and add your identikey credentials to `credentials.netrc`
    ```bash
        cp credentials.netrc.example credentials.netrc
    ```
- Create and update `vars.sh`
    ```bash
        cp vars.sh.example vars.sh
    ```

## Running the Script

1. Add run `ssh-add` in the same directory as the `migration.sh` script
2. Replace variables `env`, `backups_env`, `instance` accordingly in `migration.sh`
3. Run script simply with `./migration.sh`
