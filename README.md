# Ecumene
Advanced interaction between Destiny 2 and Discord.

## Setup
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