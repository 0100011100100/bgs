import discord
from discord.ext import commands
import random
import json
import os
from dotenv import load_dotenv
import asyncio
from datetime import datetime, timedelta

# Load environment variables
load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

DATA_FILE = "data.json"

def load_data():
    """Load user balance data from the shared data.json file."""
    try:
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError:
        print("Error decoding JSON. Creating new data file.")
        return {}

def save_data(data):
    """Save user balance data to the shared data.json file."""
    try:
        with open(DATA_FILE, "w") as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        print(f"Error saving data: {e}")

def update_user_data(user_id, coins=0, robux=0):
    """Update user data in the JSON file."""
    data = load_data()
    if user_id not in data:
        data[user_id] = {"coins": 0, "robux": 0}

    data[user_id]["coins"] = max(0, data[user_id]["coins"] + coins)
    data[user_id]["robux"] = max(0, data[user_id]["robux"] + robux)

    save_data(data)
    return data[user_id]

# Bot setup
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Cooldown tracking
user_cooldowns = {}

def is_on_cooldown(user_id):
    """Check if user is on cooldown."""
    if user_id not in user_cooldowns:
        return False

    current_time = datetime.now()
    return (current_time - user_cooldowns[user_id]).total_seconds() < 10

def set_cooldown(user_id):
    """Set cooldown for a user."""
    user_cooldowns[user_id] = datetime.now()

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

@bot.command(name="rps")
async def rps(ctx, choice: str):
    """Rock, Paper, Scissors Minigame."""
    # Cooldown check
    if is_on_cooldown(ctx.author.id):
        await ctx.send("You're on cooldown! Wait 10 seconds between games.")
        return

    options = ["rock", "paper", "scissors"]
    if choice.lower() not in options:
        await ctx.send("Invalid choice! Choose rock, paper, or scissors.")
        return

    set_cooldown(ctx.author.id)

    bot_choice = random.choice(options)
    await ctx.send(f"I chose {bot_choice}!")

    if choice.lower() == bot_choice:
        await ctx.send("It's a tie!")
    elif (
        (choice.lower() == "rock" and bot_choice == "scissors") or
        (choice.lower() == "scissors" and bot_choice == "paper") or
        (choice.lower() == "paper" and bot_choice == "rock")
    ):
        coins_won = random.randint(5, 30)
        robux_won = random.randint(1, 5)
        update_user_data(str(ctx.author.id), coins=coins_won, robux=robux_won)
        await ctx.send(f"You win! 🎉 You've earned {coins_won} coins and {robux_won} Robux.")
    else:
        coins_lost = random.randint(5, 30)
        update_user_data(str(ctx.author.id), coins=-coins_lost)
        await ctx.send(f"You lose! 😢 You've lost {coins_lost} coins.")

@bot.command(name="guess")
async def guess(ctx):
    """Number guessing game."""
    # Cooldown check
    if is_on_cooldown(ctx.author.id):
        await ctx.send("You're on cooldown! Wait 10 seconds between games.")
        return

    number = random.randint(1, 10)
    await ctx.send("Guess a number between 1 and 10!")

    def check(m):
        return m.author == ctx.author and m.channel == ctx.channel and m.content.isdigit()

    try:
        set_cooldown(ctx.author.id)
        guess = await bot.wait_for("message", check=check, timeout=15.0)
        guess = int(guess.content)

        if guess == number:
            coins_won = random.randint(10, 50)
            robux_won = random.randint(2, 7)
            update_user_data(str(ctx.author.id), coins=coins_won, robux=robux_won)
            await ctx.send(f"🎉 Correct! You've earned {coins_won} coins and {robux_won} Robux.")
        else:
            coins_lost = random.randint(10, 50)
            update_user_data(str(ctx.author.id), coins=-coins_lost)
            await ctx.send(f"😢 Wrong! The correct number was {number}. You lost {coins_lost} coins.")
    except asyncio.TimeoutError:
        await ctx.send(f"⏳ Time's up! The correct number was {number}.")

@bot.command(name="coinflip")
async def coinflip(ctx, call: str):
    """Coin Flip Minigame."""
    # Cooldown check
    if is_on_cooldown(ctx.author.id):
        await ctx.send("You're on cooldown! Wait 10 seconds between games.")
        return

    if call.lower() not in ["heads", "tails"]:
        await ctx.send("Invalid choice! Choose heads or tails.")
        return

    set_cooldown(ctx.author.id)

    result = random.choice(["heads", "tails"])
    await ctx.send(f"The coin landed on {result}!")

    if call.lower() == result:
        coins_won = random.randint(3, 20)
        robux_won = random.randint(1, 3)
        update_user_data(str(ctx.author.id), coins=coins_won, robux=robux_won)
        await ctx.send(f"🎉 You win! You've earned {coins_won} coins and {robux_won} Robux.")
    else:
        coins_lost = random.randint(3, 20)
        update_user_data(str(ctx.author.id), coins=-coins_lost)
        await ctx.send(f"You lose! 😢 You lost {coins_lost} coins.")

@bot.command(name="dice")
async def dice(ctx, bet: int):
    """Dice Rolling Minigame."""
    # Cooldown check
    if is_on_cooldown(ctx.author.id):
        await ctx.send("You're on cooldown! Wait 10 seconds between games.")
        return

    # Load user data to check coins
    data = load_data()
    user_id = str(ctx.author.id)
    user_coins = data.get(user_id, {}).get("coins", 0)

    # Check if bet is valid
    if bet <= 0 or bet > user_coins:
        await ctx.send("Invalid bet amount. Must be positive and not exceed your current coins.")
        return

    set_cooldown(ctx.author.id)

    # Roll two dice
    dice1 = random.randint(1, 6)
    dice2 = random.randint(1, 6)
    total = dice1 + dice2

    await ctx.send(f"You rolled: {dice1} and {dice2} (Total: {total})")

    if total == 7 or total == 11:
        # Big win
        winnings = bet * 2
        robux_won = random.randint(3, 8)
        update_user_data(user_id, coins=winnings, robux=robux_won)
        await ctx.send(f"🎉 Jackpot! You won {winnings} coins and {robux_won} Robux!")
    elif total in [2, 12]:
        # Extreme loss
        extreme_loss = bet * 3
        update_user_data(user_id, coins=-extreme_loss)
        await ctx.send(f"😱 Extreme loss! You lost {extreme_loss} coins!")
    elif total in [4, 5, 6, 8, 9, 10]:
        # Small win/loss
        result = random.choice([True, False])
        if result:
            winnings = bet
            update_user_data(user_id, coins=winnings)
            await ctx.send(f"👍 You won {winnings} coins!")
        else:
            update_user_data(user_id, coins=-bet)
            await ctx.send(f"👎 You lost {bet} coins!")

bot.run(DISCORD_TOKEN)