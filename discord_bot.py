
import discord
from discord import app_commands
import requests
import os

# Configuration
API_BASE_URL = "https://api.researchtwin.net" # Your Hetzner URL
BOT_TOKEN = "YOUR_DISCORD_BOT_TOKEN" # Replace with your token

class ResearchTwinBot(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        await self.tree.sync()
        print(f"Synced slash commands for {self.user}")

client = ResearchTwinBot()

@client.tree.command(name="research", description="Ask your Research Twin a question")
@app_commands.describe(query="What do you want to know about the research?", slug="The researcher's unique ID")
async def research(interaction: discord.Interaction, query: str, slug: str):
    await interaction.response.defer()

    try:
        # Call the FastAPI backend we built yesterday
        response = requests.post(
            f"{API_BASE_URL}/chat", 
            json={"message": query, "researcher_slug": slug},
            timeout=30
        )
        data = response.json()
        reply = data.get("reply", "No response from the brain.")

        # Format as a nice embed
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
    # client.run(BOT_TOKEN)
    print("Bot script ready. Replace token and run.")
