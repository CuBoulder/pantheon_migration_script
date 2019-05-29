# Web Express Migration Script

A bash script to automate moving sites from our webservers to Pantheon

## Pre-requisites

You will need to have the following items ready before using the script:

- [CU Boulder Pantheon Organization Access](https://dashboard.pantheon.io/login)

- [jq](https://stedolan.github.io/jq/) - jq is a lightweight and flexible command-line JSON processor
  
  ```bash
  brew install jq
  ```

- [Terminus](https://pantheon.io/docs/terminus/) - Terminus, provides advanced interaction with Pantheon. Terminus enables you to do almost everything in a terminal that you can do in the Dashboard, and much more. [Installation steps](https://pantheon.io/docs/terminus/install/). Make sure to follow the both the Install and Authenticate: Machine Token steps.

- Add your ssh key to the utility servers
  
- Create and add your identikey credentials to `credentials.netrc`
    ```bash
    cp credentials.netrc.example credentials.netrc
    ```
