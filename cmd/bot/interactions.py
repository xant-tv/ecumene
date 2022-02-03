import discord

# Defines a custom Select containing colour options
# that the user can choose. The callback function
# of this class is called when the user changes their choice
class EcumeneDropdown(discord.ui.Select):

    def __init__(self, options, limit=False):

        # The placeholder is what will be shown when no option is chosen
        # The min and max values indicate we can only pick one of the three options
        # The options parameter defines the dropdown options. We defined this above
        super().__init__(
            placeholder="Choose your favourite colour...",
            min_values=1,
            max_values=1,
            options=options
        )
        self.parent = None
        self.limit = limit
        self.disabled = limit

    def set_parent(self, parent: discord.Message):
        # Use this make parent message accessible within class scope.
        self.parent = parent
        self.disabled = False

    async def callback(self, interaction: discord.Interaction):
        # Use the interaction object to send a response message containing
        # the user's favourite colour or choice. The self object refers to the
        # Select object, and the values attribute gets a list of the user's
        # selected options. We only want the first one.
        #await interaction.response.send_message(
        await interaction.channel.send(
            #f"Hey {interaction.guild.default_role}, this idiot's favourite colour is {self.values[0]}. 🤣"
            f"This idiot's favourite colour is {self.values[0]}. 🤣"
        )
        if self.limit:
            # Delete attached parent if this is a one-time interaction.
            await self.parent.delete()

class EcumeneView(discord.ui.View):

    def __init__(self, children):
        super().__init__()
        for child in children:
            self.add_item(child)

    def attach_parent(self, parent):
        # Attach parent to all children.
        for child in self.children:
            child.set_parent(parent)
