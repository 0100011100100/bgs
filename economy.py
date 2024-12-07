import discord
from discord.ext import commands
from discord.ui import Button, View
import json
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

# Admin IDs and Role ID
ADMIN_IDS = [1169402125160284242, 1002396718882627585, 843507140475879514]
ADMIN_ROLE_ID = 1265407258775257229

DATA_FILE = "data.json"

EXCHANGE_RATES = {
    "Bronze": 0.001,
    "Silver": 0.01,
    "Gold": 0.05,
    "Diamond": 0.1,
    "Emerald": 0.3
}

TIERS = ["Bronze", "Silver", "Gold", "Diamond", "Emerald",]

# Robux exchangeable status
robux_exchangeable = False  # Changes to this will be managed via the admin command

def load_data():
    """Load user balance data from data.json."""
    try:
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError:
        print("Error decoding JSON. Creating new data file.")
        return {}

def save_data(data):
    """Save user balance data to data.json."""
    try:
        with open(DATA_FILE, "w") as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        print(f"Error saving data: {e}")

def get_user_tier_from_roles(member):
    """Determine a user's tier based on their roles."""
    tier_roles = [role for role in member.roles if any(role.name.startswith(tier) for tier in TIERS)]
    if not tier_roles:
        return "Bronze"
    tier_roles.sort(key=lambda r: r.position, reverse=True)
    for tier in TIERS:
        if tier_roles[0].name.startswith(tier):
            return tier
    return "Bronze"

def calculate_robux(coins, tier):
    """Calculate the Robux a user can get for their coins based on their tier."""
    rate = EXCHANGE_RATES.get(tier, 0.001)
    return round(coins * rate, 2)

# Bot setup
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

def is_admin():
    """Custom check to ensure only specified admins or users with admin role can use certain commands."""
    async def predicate(ctx):
        # Check if user is in the list of admin IDs
        if ctx.author.id in ADMIN_IDS:
            return True

        # Check if user has the specified admin role
        admin_role = ctx.guild.get_role(ADMIN_ROLE_ID)
        if admin_role in ctx.author.roles:
            return True

        return False
    return commands.check(predicate)

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

@bot.command(name="cmds")
async def show_commands(ctx):
    """Show all available commands."""
    embed = discord.Embed(
        title="🤖 Available Commands",
        description="Here are all the commands you can use:",
        color=discord.Color.blue()
    )

    # User Commands
    embed.add_field(name="👤 User Commands", value="""
    • `!bal` - Check your current balance
    • `!bal @user` - Check another user's balance
    • `!exchange` - Exchange coins for Robux
    • `!daily` - Claim your daily coins
    """, inline=False)

    # Admin Commands
    embed.add_field(name="🛡️ Admin Commands", value="""
    • `!admin reset @user` - Reset user's balance to zero
    • `!admin delete @user` - Delete user's balance entry
    • `!admin add @user [coins] [robux]` - Add coins/Robux to user
    • `!admin remove @user [coins] [robux]` - Remove coins/Robux from user
    • `!admin allowrobux` - Toggle the exchangeable status of Robux
    """, inline=False)

    # Tier Information
    embed.add_field(name="📊 Tier Information", value=f"""
    Tiers: {', '.join(TIERS)}
    Exchange Rates:
    {', '.join(f'{tier}: {rate}' for tier, rate in EXCHANGE_RATES.items())}
    """, inline=False)

    embed.set_footer(text="Use these commands to manage your balance and exchange coins!")

    await ctx.send(embed=embed)

@bot.command(name="bal")
async def bal(ctx, member: discord.Member = None):
    """Check the balance of a user."""
    member = member or ctx.author
    user_id = str(member.id)
    data = load_data()
    if user_id not in data:
        data[user_id] = {"coins": 0, "robux": 0}
        save_data(data)
    coins = data[user_id].get("coins", 0)
    robux = data[user_id].get("robux", 0)
    tier = get_user_tier_from_roles(member)
    potential_robux = calculate_robux(coins, tier)

    embed = discord.Embed(title=f"{member.name}'s Balance", color=discord.Color.green())
    embed.set_thumbnail(url=member.avatar.url)
    embed.add_field(name="Coins", value=f"{coins}", inline=True)
    embed.add_field(name="Current Robux", value=f"{robux} Robux", inline=True)
    embed.add_field(name="Tier", value=tier, inline=True)

    # Show potential Robux exchange info
    if coins >= 100:
        embed.add_field(name="Potential Robux Exchange", value=f"{potential_robux} Robux", inline=False)

    # Show exchangeable status
    exchangeable_status = "Currently exchangeable." if robux_exchangeable else "Currently unexchangeable."
    embed.add_field(name="Robux Exchange Status", value=exchangeable_status, inline=False)

    await ctx.send(embed=embed)

@bot.command(name="exchange")
async def exchange(ctx):
    """Exchange coins for Robux."""
    user_id = str(ctx.author.id)
    data = load_data()
    if user_id not in data:
        data[user_id] = {"coins": 0, "robux": 0}
        save_data(data)
    coins = data[user_id].get("coins", 0)
    tier = get_user_tier_from_roles(ctx.author)

    if coins < 100:
        await ctx.send("You need at least 100 coins to exchange.")
        return

    # Check if Robux is exchangeable before proceeding
    if not robux_exchangeable:
        await ctx.send("Robux is currently unexchangeable.")
        return

    view = View()
    exchange_amounts = [100, 500, 1000, 2000, 5000, 10000, 100000, 99999999999,]
    for amount in exchange_amounts:
        if coins >= amount:
            potential_robux = calculate_robux(amount, tier)
            exchange_button = Button(
                label=f"Exchange {amount} coins for {potential_robux} Robux",
                style=discord.ButtonStyle.green
            )

            async def create_exchange_callback(interaction, exchange_amount=amount):
                """Handle the exchange process."""
                current_data = load_data()
                current_coins = current_data[user_id].get("coins", 0)
                if current_coins < exchange_amount:
                    await interaction.response.send_message("Not enough coins!", ephemeral=True)
                    return
                robux_amount = calculate_robux(exchange_amount, tier)
                current_data[user_id]["coins"] -= exchange_amount
                current_data[user_id]["robux"] += robux_amount
                save_data(current_data)
                await interaction.response.send_message(
                    f"Successfully exchanged {exchange_amount} coins for {robux_amount} Robux!",
                    ephemeral=True
                )

            exchange_button.callback = create_exchange_callback
            view.add_item(exchange_button)

    embed = discord.Embed(
        title="Robux Exchange",
        description="Select the amount of coins you want to exchange",
        color=discord.Color.blue()
    )
    embed.add_field(name="Current Tier", value=tier, inline=True)
    embed.add_field(name="Current Coins", value=f"{coins}", inline=True)
    await ctx.send(embed=embed, view=view)

@bot.command(name="daily")
@commands.cooldown(1, 86400, commands.BucketType.user)
async def daily(ctx):
    """Claim daily coins."""
    daily_reward = 100
    user_id = str(ctx.author.id)
    data = load_data()
    if user_id not in data:
        data[user_id] = {"coins": 0, "robux": 0}
    data[user_id]["coins"] += daily_reward
    save_data(data)
    await ctx.send(f"{ctx.author.mention}, you've claimed {daily_reward} coins as your daily reward!")

@bot.command(name="admin")
@is_admin()
async def admin_commands(ctx, action: str, member: discord.Member = None, coins: int = 0, robux: float = 0):
    """
    Simplified admin command for balance management.

    Usage:
    !admin reset @user - Reset balance to zero
    !admin delete @user - Delete balance entry
    !admin add @user [coins] [robux] - Add balance
    !admin remove @user [coins] [robux] - Remove balance
    !admin allowrobux - Toggle the exchangeable status of Robux
    """
    if action.lower() == 'allowrobux':
        global robux_exchangeable
        robux_exchangeable = not robux_exchangeable
        status = "exchangeable" if robux_exchangeable else "unexchangeable"
        await ctx.send(f"Robux is now marked as {status}.")
        return

    if not member:
        await ctx.send("Please specify a user.")
        return

    user_id = str(member.id)
    data = load_data()

    if action.lower() == 'reset':
        # Reset balance to zero
        if user_id in data:
            data[user_id]["coins"] = 0
            data[user_id]["robux"] = 0
        else:
            data[user_id] = {"coins": 0, "robux": 0}
        save_data(data)
        await ctx.send(f"{member.name}'s balance has been reset to zero.")

    elif action.lower() == 'delete':
        # Delete user's balance entry
        if user_id in data:
            del data[user_id]
            save_data(data)
            await ctx.send(f"{member.name}'s balance entry has been deleted.")
        else:
            await ctx.send(f"{member.name} does not have a balance entry.")

    elif action.lower() == 'add':
        # Add specified amounts
        if user_id not in data:
            data[user_id] = {"coins": 0, "robux": 0}
        data[user_id]["coins"] += coins
        data[user_id]["robux"] += robux
        save_data(data)
        await ctx.send(f"Added {coins} coins and {robux} Robux to {member.name}'s balance.")

    elif action.lower() == 'remove':
        # Remove specified amounts
        if user_id in data:
            data[user_id]["coins"] = max(0, data[user_id].get("coins", 0) - coins)
            data[user_id]["robux"] = max(0, data[user_id].get("robux", 0) - robux)
            save_data(data)
            await ctx.send(f"Removed {coins} coins and {robux} Robux from {member.name}'s balance.")
        else:
            await ctx.send(f"{member.name} does not have a balance entry.")

    else:
        await ctx.send("Invalid action. Use reset, delete, add, remove, or allowrobux.")

# Run the bot
bot.run(DISCORD_TOKEN)