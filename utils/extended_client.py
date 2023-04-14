import discord

class ExtendedClient(discord.Client):
    def __init__(self, required_channel: str) -> None:
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(intents=intents)
        
        self.channel = None
        self.required_channel = required_channel
        
    async def on_ready(self) -> None:
        print(f"Logged on as: {self.user}!")
        
    async def setup_hook(self) -> None:
        self.bg_task = self.loop.create_task(self.bg_notification_task())
        
    async def bg_notification_task(self) -> None:
        pass
        
    async def notification(self) -> None:
        pass
    
    def set_channel(self, voice=False) -> None:
        for guild in self.guilds:
            channels = guild.channels if not voice else guild.voice_channels
            for c in channels:
                if c.name == self.required_channel:
                    self.channel = c
    
    def bold(self, text):
        return(f"**{text}**")

