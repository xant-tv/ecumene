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
BNET_ENDPOINT=https://www.bungie.net/Platform
BNET_API_KEY=<your_api_key>

# Discord
DISCORD_TOKEN=<your_token>
DISCORD_GUILD_ID=<dev_server_id> # Should be removed in production.
```
Note that Discord rolls out updates to application commands with up to an hour delay. However, guild-specific commands are updated immediately. Setting the `DISCORD_GUILD_ID` to a specific server will allow rapid testing of the application slash commands. However, this variable should be left empty when deployed.

## Requirements
 - `py-cord 2.0.0+` (still in pre-release)
 - `flask`