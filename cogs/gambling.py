# gambling.py
import discord
from discord import app_commands
from discord.ext import commands
import random
import json
import os
from typing import List, Tuple

SCORE_FILE = "casino_scores.json"


def load_scores():
    if not os.path.exists(SCORE_FILE):
        return {}
    try:
        with open(SCORE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_scores(data):
    tmp = SCORE_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp, SCORE_FILE)


def ensure_user_entry(data: dict, user_id: str):
    if user_id not in data:
        data[user_id] = {
            "blackjack": {"wins": 0, "losses": 0, "ties": 0},
            "high_low": {"wins": 0, "losses": 0, "ties": 0},
        }


def update_score(user_id: int, game: str, result: str):
    """
    result: "win", "loss", or "tie"
    game: "blackjack" or "high_low"
    """
    data = load_scores()
    uid = str(user_id)
    ensure_user_entry(data, uid)
    if result == "win":
        data[uid][game]["wins"] += 1
    elif result == "loss":
        data[uid][game]["losses"] += 1
    elif result == "tie":
        data[uid][game]["ties"] += 1
    save_scores(data)


# ---- Card utilities ----
RANKS = ["A"] + [str(n) for n in range(2, 11)] + ["J", "Q", "K"]
SUITS = ["♠", "♥", "♦", "♣"]


def new_shuffled_deck() -> List[Tuple[str, str]]:
    deck = [(rank, suit) for rank in RANKS for suit in SUITS]
    random.shuffle(deck)
    return deck


def card_str(card: Tuple[str, str]) -> str:
    return f"{card[0]}{card[1]}"


def card_value(rank: str) -> int:
    if rank in ("J", "Q", "K"):
        return 10
    if rank == "A":
        return 11  # initially treat Ace as 11; adjust later
    return int(rank)


def hand_best_total(hand: List[Tuple[str, str]]) -> int:
    # sum with Aces as 11 then reduce as needed
    total = 0
    aces = 0
    for rank, _ in hand:
        if rank == "A":
            aces += 1
            total += 11
        else:
            total += card_value(rank)
    # reduce aces from 11 to 1 as needed
    while total > 21 and aces:
        total -= 10
        aces -= 1
    return total


# ---- Views ----

class BlackjackView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)
        self.deck = new_shuffled_deck()
        # Draw player two cards, dealer one visible and one hole
        self.player_hand: List[Tuple[str, str]] = [self.draw_card(), self.draw_card()]
        self.dealer_hand: List[Tuple[str, str]] = [self.draw_card(), self.draw_card()]
        self.game_over = False
        self.message: discord.Message | None = None

    def draw_card(self) -> Tuple[str, str]:
        if not self.deck:
            self.deck = new_shuffled_deck()
        return self.deck.pop()

    async def on_timeout(self):
        if self.game_over or not self.message:
            return
        embed = discord.Embed(
            title="Game Over",
            description="Blackjack timed out due to inactivity.",
            color=discord.Color.red(),
        )
        await self.message.edit(embed=embed, view=None)
        self.stop()

    def visible_dealer_display(self) -> str:
        # show first dealer card and a hidden placeholder for second
        first = card_str(self.dealer_hand[0])
        return f"{first}, [Hidden]"

    async def update_message(self, interaction: discord.Interaction):
        player_total = hand_best_total(self.player_hand)
        embed = discord.Embed(
            title="Blackjack",
            description=(
                f"Your hand: {[card_str(c) for c in self.player_hand]} (Total: {player_total})\n"
                f"Dealer: {self.visible_dealer_display()}"
            ),
            color=discord.Color.green(),
        )
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Hit", style=discord.ButtonStyle.green)
    async def hit(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.game_over:
            # ephemeral because interaction is already over
            await interaction.response.send_message("Game already finished. Start a new one.", ephemeral=True)
            return

        self.player_hand.append(self.draw_card())
        player_total = hand_best_total(self.player_hand)

        if player_total > 21:
            # player busts
            self.game_over = True
            embed = discord.Embed(
                title="Bust!",
                description=(
                    f"You busted with {[card_str(c) for c in self.player_hand]} (Total: {player_total}).\n"
                    f"Dealer wins."
                ),
                color=discord.Color.red(),
            )
            await interaction.response.edit_message(embed=embed, view=None)
            update_score(interaction.user.id, "blackjack", "loss")
            self.stop()
            return

        await self.update_message(interaction)

    @discord.ui.button(label="Stand", style=discord.ButtonStyle.red)
    async def stand(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.game_over:
            await interaction.response.send_message("Game already finished. Start a new one.", ephemeral=True)
            return

        # Dealer reveals hole and plays
        while hand_best_total(self.dealer_hand) < 17:
            self.dealer_hand.append(self.draw_card())

        player_total = hand_best_total(self.player_hand)
        dealer_total = hand_best_total(self.dealer_hand)

        if dealer_total > 21:
            result = "You win! Dealer busted."
            color = discord.Color.green()
            outcome = "win"
        elif player_total > dealer_total:
            result = "You win!"
            color = discord.Color.green()
            outcome = "win"
        elif player_total < dealer_total:
            result = "Dealer wins!"
            color = discord.Color.red()
            outcome = "loss"
        else:
            result = "It's a tie!"
            color = discord.Color.gold()
            outcome = "tie"

        self.game_over = True
        embed = discord.Embed(
            title="Blackjack - Result",
            description=(
                f"Your hand: {[card_str(c) for c in self.player_hand]} (Total: {player_total})\n"
                f"Dealer's hand: {[card_str(c) for c in self.dealer_hand]} (Total: {dealer_total})\n\n"
                f"{result}"
            ),
            color=color,
        )
        await interaction.response.edit_message(embed=embed, view=None)
        update_score(interaction.user.id, "blackjack", outcome)
        self.stop()


class HighLowView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)
        self.current_number = random.randint(1, 100)
        self.score = 0
        self.game_over = False
        self.message: discord.Message | None = None

    async def on_timeout(self):
        if self.game_over or not self.message:
            return
        embed = discord.Embed(title="Timeout", description="High-Low timed out.", color=discord.Color.red())
        await self.message.edit(embed=embed, view=None)
        self.stop()

    async def update_message(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="High Low",
            description=f"Current number: {self.current_number}\nScore: {self.score}",
            color=discord.Color.blue(),
        )
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Higher", style=discord.ButtonStyle.green)
    async def higher(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.game_over:
            await interaction.response.send_message("Game already ended. Start a new one.", ephemeral=True)
            return

        next_number = random.randint(1, 100)
        if next_number > self.current_number:
            self.score += 1
            self.current_number = next_number
            await self.update_message(interaction)
            return

        # wrong guess
        self.game_over = True
        embed = discord.Embed(
            title="Game Over",
            description=f"You guessed wrong! Next number was {next_number}. Final score: {self.score}",
            color=discord.Color.red(),
        )
        await interaction.response.edit_message(embed=embed, view=None)
        # define win/loss: let's say score >= 1 is a "win" for fun, else loss.
        if self.score > 0:
            result = "win"
        else:
            result = "loss"
        update_score(interaction.user.id, "high_low", result)
        self.stop()

    @discord.ui.button(label="Lower", style=discord.ButtonStyle.red)
    async def lower(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.game_over:
            await interaction.response.send_message("Game already ended. Start a new one.", ephemeral=True)
            return

        next_number = random.randint(1, 100)
        if next_number < self.current_number:
            self.score += 1
            self.current_number = next_number
            await self.update_message(interaction)
            return

        self.game_over = True
        embed = discord.Embed(
            title="Game Over",
            description=f"You guessed wrong! Next number was {next_number}. Final score: {self.score}",
            color=discord.Color.red(),
        )
        await interaction.response.edit_message(embed=embed, view=None)
        if self.score > 0:
            result = "win"
        else:
            result = "loss"
        update_score(interaction.user.id, "high_low", result)
        self.stop()


# ---- Cog ----

class Gambling(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="blackjack", description="Play a game of blackjack")
    async def blackjack(self, interaction: discord.Interaction):
        view = BlackjackView()
        embed = discord.Embed(
            title="Blackjack",
            description=(
                f"Your hand: {[card_str(c) for c in view.player_hand]} (Total: {hand_best_total(view.player_hand)})\n"
                f"Dealer: {view.visible_dealer_display()}"
            ),
            color=discord.Color.green(),
        )
        await interaction.response.send_message(embed=embed, view=view)
        # store message so timeout can edit it
        view.message = await interaction.original_response()

    @app_commands.command(name="high_low", description="Play High-Low")
    async def high_low(self, interaction: discord.Interaction):
        view = HighLowView()
        embed = discord.Embed(
            title="High Low",
            description=f"Current number: {view.current_number}\nScore: {view.score}",
            color=discord.Color.blue(),
        )
        await interaction.response.send_message(embed=embed, view=view)
        view.message = await interaction.original_response()

    @app_commands.command(name="casino_stats", description="Show your casino scoreboard")
    async def casino_stats(self, interaction: discord.Interaction):
        data = load_scores()
        uid = str(interaction.user.id)
        if uid not in data:
            await interaction.response.send_message("No stats found for you yet.", ephemeral=True)
            return
        bj = data[uid]["blackjack"]
        hl = data[uid]["high_low"]
        embed = discord.Embed(title=f"{interaction.user.display_name}'s Casino Stats", color=discord.Color.blurple())
        embed.add_field(
            name="Blackjack",
            value=f"Wins: {bj['wins']}\nLosses: {bj['losses']}\nTies: {bj['ties']}",
            inline=True,
        )
        embed.add_field(
            name="High-Low",
            value=f"Wins: {hl['wins']}\nLosses: {hl['losses']}\nTies: {hl['ties']}",
            inline=True,
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot):
    await bot.add_cog(Gambling(bot))
