
import discord
from discord import app_commands
import requests
import os

# Configuration from environment (set in docker-compose.yml)
API_BASE_URL = os.environ.get("API_BASE_URL", "http://backend:8000")
BOT_TOKEN = os.environ.get("DISCORD_BOT_TOKEN", "")

class ResearchTwinBot(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        # Sync to specific guild for instant availability
        guild_id = os.environ.get("DISCORD_GUILD_ID", "")
        if guild_id:
            guild = discord.Object(id=int(guild_id))
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
            print(f"Synced slash commands to guild {guild_id}")
        # Also sync globally (takes up to 1hr to propagate)
        try:
            await self.tree.sync()
            print(f"Synced global slash commands for {self.user}")
        except Exception as e:
            print(f"Global sync failed (non-critical): {e}")

client = ResearchTwinBot()

@client.tree.command(name="research", description="Ask your Research Twin a question")
@app_commands.describe(query="What do you want to know about the research?", slug="The researcher's unique ID")
async def research(interaction: discord.Interaction, query: str, slug: str):
    await interaction.response.defer()

    try:
        response = requests.post(
            f"{API_BASE_URL}/chat",
            json={"message": query, "researcher_slug": slug},
            timeout=30,
        )
        if response.status_code == 503:
            await interaction.followup.send("Daily chat limit reached — try again tomorrow.")
            return
        if response.status_code == 429:
            await interaction.followup.send("Too many requests — please wait a bit and try again.")
            return
        if response.status_code == 504:
            await interaction.followup.send("Request timed out — try a simpler question.")
            return
        if response.status_code == 404:
            await interaction.followup.send(f"Researcher `{slug}` not found. Check the slug and try again.")
            return

        data = response.json()
        reply = data.get("reply", "No response from the brain.")

        embed = discord.Embed(title=f"Research Query: {slug}", description=reply, color=0x3498db)
        embed.set_footer(text="Powered by ResearchTwin.net | BGNO Architecture")
        await interaction.followup.send(embed=embed)
    except Exception as e:
        await interaction.followup.send(f"Error connecting to ResearchTwin: {str(e)}")

@client.tree.command(name="sindex", description="Check a researcher's real-time S-index")
async def sindex(interaction: discord.Interaction, slug: str):
    await interaction.response.defer()

    try:
        # Call the context endpoint to get S-index metrics
        response = requests.get(f"{API_BASE_URL}/api/context/{slug}", timeout=15)
        data = response.json()

        s_score = data.get("s_index", 0)

        embed = discord.Embed(title=f"S-Index Report: {slug}", color=0x2ecc71)
        embed.add_field(name="Current S-Index", value=f"**{s_score:.2f}**", inline=False)
        embed.add_field(name="Status", value="🚀 Impact Trending Up" if s_score > 10 else "📈 Growing Utility")
        embed.set_footer(text="Metrics: Citations + Code Utility + Data Reuse")

        await interaction.followup.send(embed=embed)
    except Exception as e:
        await interaction.followup.send(f"Could not calculate S-index: {str(e)}")

if __name__ == '__main__':
    if not BOT_TOKEN:
        print("ERROR: DISCORD_BOT_TOKEN not set")
        exit(1)
    client.run(BOT_TOKEN)
