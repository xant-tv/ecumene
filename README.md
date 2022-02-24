# Ecumene
Advanced interaction between Destiny 2 and Discord.

## Setup
TBD

### Oracle Cloud
Talk through
 - Provisioning of compartment, 
 - database (make a user through the UI),
 - VCN (create first, set up security list rules), 
 - IPs (just search for this one it's easy), 
 - compute, 
 - vault (also easy - so far!)

#### VCN:
 - Open ports via security list

#### Compute:
Run some basic firewalld commands
 `sudo firewall-cmd --zone=public --permanent --add-port=<your_port>/<protocol>`
 `sudo firewall-cmd --reload`

Information [here](https://access.redhat.com/documentation/en-us/red_hat_enterprise_linux/7/html/security_guide/sec-setting_and_controlling_ip_sets_using_firewalld) around how to blacklist IPs:

Install the following:
 - [docker](https://docs.docker.com/engine/install/rhel/)
 - [Configure docker to start on boot](https://docs.docker.com/engine/install/linux-postinstall/#configure-docker-to-start-on-boot)
 - certbot
 - [oci](https://docs.oracle.com/en-us/iaas/Content/API/SDKDocs/cliinstall.htm)

#### Certbot
Needed to manually set up CRON to renew:
`echo "30 0,12 * * * root certbot renew -q" | sudo tee -a /etc/crontab > /dev/null`

#### OCI CLI Tools:
TBD

## Contributing
Bear the following in mind when setting up an environment for contributing.

Create a `.env` file within `ecumene` similar to the example provided. This ensures no secrets are stored within version control.

```python
# Environment - Example Configuration

# BNET
BNET_ENDPOINT=https://www.bungie.net
BNET_API_KEY=<your_api_key>
BNET_CLIENT_ID=<your_client_id>
BNET_CLIENT_SECRET=<your_client_secret>

# Discord
DISCORD_WEB_ROOT=https://discord.com
DISCORD_TOKEN=<your_token>
DISCORD_GUILD_ID=<dev_server_id> # Should be removed in production.

# Database
DB_USER=<your_db_user>
DB_PASSWORD=<your_db_pass>
DB_SID=<sid>

# Flask
SECRET_KEY=<your_secret_key>
```
Note that Discord rolls out updates to application commands with up to an hour delay. However, guild-specific commands are updated immediately. Setting the `DISCORD_GUILD_ID` to a specific server will allow rapid testing of the application slash commands. However, this variable should be left empty when deployed.

## Requirements
 - `py-cord 2.0.0+` (still in pre-release)
 - `flask`