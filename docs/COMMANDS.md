# Commands
The following commands are available. Note that the majority are grouped by their intended purpose and expected level of permissions.

## Identity
Commands in this category are unrestricted and intended to be used by all users for identity management.

| Command | Purpose |
| ------- | ------- |
| `/register` | User registration just like other bots. |
| `/profile` | Allows non cross-save users to select an active platform. |
| `/inspect` | Will return the user's registered details and platforms. |

## Admin
This category holds all functionality related to configuring the Destiny 2 side of clan administration.

| Command | Purpose |
| ------- | ------- |
| `/admin register <id> <role>` | Setup process to tell Ecumene to manage a clan within a particular server. |
| `/admin deregister <id>` | Removes that clan from Ecumene administration. |
| `/admin list` | Lists which clans are currently managed by Ecumene. |

Commands in this group are restricted to server administration permissions only.

## Guild
This category holds all functionality related to configuring command roles on the Discord server.

| Command | Purpose |
| ------- | ------- |
| `/guild grant <role> <command>` | Configure for the selected role. |
| `/guild revoke <role> <command>` | Undoes the grant. |
| `/guild clear role <role>` | Clears all permissions for that role. |
| `/guild clear command <command>` | Clears all permissions for that command. |
| `/guild clear all` | Resets all non-default permissions for this guild. |
| `/guild roles <command>` | List all roles with permissions to run a command. |
| `/guild command <roles>` | List all commands able to be run by the specific role. |
| `/guild block <user>` | Restrict a user from using role-based commands in this server even if they have the appropriate roles. Admins cannot be blocked. |
| `/guild unblock <user>` | Unblock a user. |

Commands in this group are restricted to server administration permissions only.

## Clan
Commands here allow for direct in-game clan interaction.

| Command | Purpose |
| ------- | ------- |
| `/clan list <filter>` | Get a list of all users in all clans including Bungie and Discord names, activity levels and so on. |
| `/clan kick <user>` | Kick a user from any Destiny 2 clan managed by Ecumene. |
| `/clan join <role>` | Prompt the administrator of the mentioned clan to send the user an invite to join the clan. |
| `/clan rank <user> <rank>` | Promote or demote a user within the Destiny 2 clan. |
| `/clan action <method> <user>` | Allows for limited but direct interaction with users or clans that are not registered or in the server. |

Commands in this group utilise role-based access according to the guild setup. This allows appointing non-server administrators as clan administrators.

## Audit
All robot commands are auditable via commands in this group.

| Command | Purpose |
| ------- | ------- |
| `/audit all <period>` | Will give you some information about who ran this command recently. |

Commands in this group are restricted to server administration permissions only.