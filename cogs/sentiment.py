import discord
from discord.ext import commands
from discord import app_commands
import nltk
from concurrent.futures import ThreadPoolExecutor
import functools
import asyncio

nltk.download('vader_lexicon')

from nltk.sentiment import SentimentIntensityAnalyzer
from rapidfuzz import fuzz


class SentimentCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.sentiment = SentimentIntensityAnalyzer()
        self.pool = ThreadPoolExecutor(max_workers=8)


    @staticmethod
    def fuzzyMatch(subject: str, content: str) -> float:
        return fuzz.partial_ratio(subject.lower(), content.lower())

    @app_commands.command(
        name="historical-sentiment",
        description="Analyze topic-based sentiment over recent messages."
    )
    async def historicalSentiment(
        self,
        interaction: discord.Interaction,
        subject: str,
        channel: discord.TextChannel = None,
        limit: int = 1000,
        fuzzymatchthreshold: int = 70
    ):
        channel = channel or interaction.channel

        await interaction.response.send_message(
            f"Fetching {limit} messages from {channel.mention}...Estimated Time... {int(1000 * limit / 131)} ms.",
            ephemeral=True
        )
        start_time = discord.utils.utcnow()

        messages = [m async for m in channel.history(limit=limit)]
        messages.reverse()  # chronological order

        # Parallelize fuzzy matching + VADER scoring using the thread pool.
        # We compute fuzz scores and VADER polarity scores in batches to
        # reduce wall-time compared to per-message synchronous processing.
        subject_lower = subject.lower()
        scores = [0] * len(messages)
        vader_results = [None] * len(messages)

        loop = asyncio.get_running_loop()
        batch_size = 256

        def process_batch(batch):
            out = []
            for i, m in batch:
                txt = m.content or ""
                if not txt.strip():
                    out.append((i, 0, None))
                    continue
                txt_lower = txt.lower()
                # fast substring check before expensive fuzzy
                quick_hit = subject_lower in txt_lower
                fuzz_score = 100 if quick_hit else fuzz.partial_ratio(subject_lower, txt_lower)
                vader = self.sentiment.polarity_scores(txt)
                out.append((i, fuzz_score, vader))
            return out

        futures = []
        items = [(i, m) for i, m in enumerate(messages)]
        for i in range(0, len(items), batch_size):
            chunk = items[i:i+batch_size]
            futures.append(loop.run_in_executor(self.pool, functools.partial(process_batch, chunk)))

        if futures:
            batches = await asyncio.gather(*futures)
            for batch in batches:
                for i, sc, vader in batch:
                    scores[i] = sc
                    vader_results[i] = vader

        core_hits = [i for i, s in enumerate(scores) if s >= fuzzymatchthreshold]

        if not core_hits:
            await interaction.followup.send(
                f"No messages found about '{subject}'."
            )
            return

        blocks = []
        current_block = [core_hits[0]]

        for idx in core_hits[1:]:
            if idx - current_block[-1] <= 3:
                current_block.append(idx)
            else:
                blocks.append(current_block)
                current_block = [idx]

        blocks.append(current_block)

        expanded_blocks = []
        max_gap = 2       
        max_time_gap = 120

        for b in blocks:
            start = max(0, b[0] - 1)  
            end = b[-1]

            gap_count = 0
            i = end + 1
            while i < len(messages):
                time_diff = (messages[i].created_at - messages[i - 1].created_at).total_seconds()

                if scores[i] >= fuzzymatchthreshold:
                    gap_count = 0
                    end = i
                elif gap_count < max_gap and time_diff <= max_time_gap:
                    gap_count += 1
                    end = i
                else:
                    break

                i += 1

            expanded_blocks.append((start, end))

        merged = []
        for start, end in expanded_blocks:
            if not merged or start > merged[-1][1]:
                merged.append([start, end])
            else:
                merged[-1][1] = max(merged[-1][1], end)

        relevant_indices = set()
        for start, end in merged:
            for i in range(start, end + 1):
                relevant_indices.add(i)

        relevant_messages = [messages[i] for i in sorted(relevant_indices)]

        results = []
        for m in relevant_messages:
            sc = self.sentiment.polarity_scores(m.content)
            comp = sc["compound"]
            if comp > 0:
                sent = "positive"
            elif comp < 0:
                sent = "negative"
            else:
                sent = "neutral"
            results.append((m.content, sent, comp))

        avg = sum(r[2] for r in results) / len(results)
        pos = len([r for r in results if r[1] == "positive"])
        neg = len([r for r in results if r[1] == "negative"])
        neu = len([r for r in results if r[1] == "neutral"])
        end_time = discord.utils.utcnow()
        msgRate = limit / (end_time - start_time).total_seconds()

        embed = discord.Embed(
            title="Topic Block Sentiment Analysis",
            description=(
                f"Subject: **{subject}**\n"
                f"Blocks found: **{len(merged)}**\n"
                f"Total messages analyzed: **{len(results)}** out of **{limit}** messages\n"
                f"Average sentiment score: **{avg:.3f}**\n"
                f"Elapsed time: **{(end_time - start_time).total_seconds():.2f}** seconds (**{msgRate:.3f}** messages per second)**"
            ),
            color=discord.Color.blurple()
        )

        embed.add_field(name="Positive", value=pos)
        embed.add_field(name="Negative", value=neg)
        embed.add_field(name="Neutral", value=neu)

        await interaction.followup.send(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(SentimentCog(bot))