import logging
import discord

# Defines a confirmation dialog.
class EcumeneConfirm(discord.ui.View):

    def __init__(self):
        super().__init__()
        self.value = None

    # On press set inner value and stop the view from listening to more input.
    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.green)
    async def confirm(self, button: discord.ui.Button, interaction: discord.Interaction):
        self.value = True
        self.stop()

    # Similar except record cancel.
    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.grey)
    async def cancel(self, button: discord.ui.Button, interaction: discord.Interaction):
        self.value = False
        self.stop()

class EcumeneConfirmKick(discord.ui.View):

    def __init__(self):
        super().__init__()
        self.value = None

    # On press set inner value and stop the view from listening to more input.
    @discord.ui.button(label="Kick", style=discord.ButtonStyle.red)
    async def confirm(self, button: discord.ui.Button, interaction: discord.Interaction):
        self.value = True
        self.stop()

    # Similar except record cancel.
    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.grey)
    async def cancel(self, button: discord.ui.Button, interaction: discord.Interaction):
        self.value = False
        self.stop()

class EcumeneConfirmRemoveClan(discord.ui.View):

    def __init__(self):
        super().__init__()
        self.value = None

    # On press set inner value and stop the view from listening to more input.
    @discord.ui.button(label="Remove", style=discord.ButtonStyle.red)
    async def confirm(self, button: discord.ui.Button, interaction: discord.Interaction):
        self.value = True
        self.stop()

    # Similar except record cancel.
    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.grey)
    async def cancel(self, button: discord.ui.Button, interaction: discord.Interaction):
        self.value = False
        self.stop()

# Defines a custom dropdown that is built dynamically.
# We have to do this as decorators require fixed options.
# However, platform options need to be built per request.
class EcumenePlatformDropdown(discord.ui.Select):

    def __init__(self, options):
        # The placeholder is what will be shown when no option is chosen.
        # The min and max values indicate we can only pick one of the three options
        # The options parameter defines the dropdown options. We defined this above
        super().__init__(
            placeholder="Choose your preferred platform...",
            min_values=1,
            max_values=1,
            options=options
        )

    async def callback(self, interaction: discord.Interaction):
        # Use the interaction object to send a response message if need be.
        # In this case, we capture value within the view object and then stop interaction.
        self.view.value = self.values[0]
        self.view.stop()

class EcumeneSelectPlatform(discord.ui.View):

    def __init__(self, dropdown):
        super().__init__()
        self.add_item(dropdown)
        self.value = None