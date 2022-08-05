import discord

from bot.core.checks import get_lineage
from util.enum import AuditRecordType
from util.time import get_current_time

class AuditRecord():
    """Auditable record object class."""
    def __init__(
        self, record_id, 
        command_id, invoked_at, guild_id, discord_id, 
        options, status
    ):
        # Basically just store these as object properties.
        self.id = record_id
        self.command_id = command_id
        self.invoked_at = invoked_at
        self.guild_id = guild_id
        self.discord_id = discord_id
        self.options = options
        self.status = status

    def as_data(self, non_null_only=True):
        """
        Return as a data structure.
        Optionally choose to return all values or non-nulls only.
        """
        # All data as a structure.
        all_data = {
            'record_id': self.id,
            'command_id': self.command_id,
            'invoked_at': self.invoked_at,
            'guild_id': self.guild_id,
            'discord_id': self.discord_id,
            'command_options': self.options,
            'status': self.status
        }
        if not non_null_only:
            return all_data

        # Limit to only non-null values.
        data = dict()
        for key, value in all_data.items():
            if value is not None:
                data[key] = value
        return data

def format_command_options(ctx: discord.ApplicationContext):
    """
    Unpack and format command options.
    This returns a string we can push into a database.
    """
    if not ctx.selected_options:
        return None

    options = list()
    for option in ctx.selected_options:
        # Record the name of the variable and the value.
        name = option.get('name')
        value = option.get('value')
        # Can't really foresee a case where this isn't a primitive or a list of primitives.
        value_str = 'None',
        if isinstance(value, list):
            value_str = ','.join(map(str, value))
        elif value:
            value_str = str(value)
        option_str = f'{name}={value_str}'
        options.append(option_str)
    
    formatted_options = ';'.join(options)
    return formatted_options

def generate_command_record(ctx: discord.ApplicationContext, status=AuditRecordType.PENDING, stub=False):
    """Generates auditable command record."""
    
    invoked_at = None
    if not stub:
        invoked_at = get_current_time()

    # Get lineage and command identifier.
    lineage = list()
    lineage = get_lineage(ctx.command, lineage)
    command_id = '.'.join(reversed(lineage))
    
    # Formatted commands (if they exist).
    formatted_options = None
    if not stub:
        formatted_options = format_command_options(ctx)

    record = AuditRecord(
        str(ctx.interaction.id), 
        command_id,
        invoked_at,
        str(ctx.guild_id), 
        str(ctx.author.id), 
        formatted_options, 
        status.value
    )

    return record