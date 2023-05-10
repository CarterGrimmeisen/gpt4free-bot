import re
from os import getenv

import discord
from discord import ApplicationContext, Option
from discord.message import DeletedReferencedMessage, Message
from dotenv import load_dotenv
from gpt4free import you
from playhouse.shortcuts import model_to_dict

from gpt4free_bot.models import DEFAULT_SETTINGS, Settings, SettingsDict, db

load_dotenv()
bot = discord.Bot()


@bot.event
async def on_ready():
    db.connect()
    db.create_tables([Settings], safe=True)
    print("Bot is ready.")


@bot.command(name="context", description="Set the number of context messages.")
async def set_context(ctx: ApplicationContext, count: Option(int)):  # type: ignore
    if not ctx.guild:
        await ctx.respond("This command can only be used in a server.", ephemeral=True)
        return

    with db.atomic():
        (
            Settings.update(context_message_count=count)
            .where(Settings.guild == str(ctx.guild.id))
            .execute()
        )

    await ctx.respond("Context updated.", ephemeral=True)


@bot.command(name="persona", description="Set the bot's persona.")
async def set_persona(ctx: ApplicationContext, persona: Option(str)):  # type: ignore
    if not ctx.guild:
        await ctx.respond("This command can only be used in a server.", ephemeral=True)
        return

    with db.atomic():
        (
            Settings.update(persona=persona)
            .where(Settings.guild == str(ctx.guild.id))
            .execute()
        )

    await ctx.respond("Persona updated.", ephemeral=True)


@bot.command(name="clearpersona", description="Clear the bot's persona.")
async def clear_persona(ctx: ApplicationContext):  # type: ignore
    if not ctx.guild:
        await ctx.respond("This command can only be used in a server.", ephemeral=True)
        return

    with db.atomic():
        (
            Settings.update(persona="")
            .where(Settings.guild == str(ctx.guild.id))
            .execute()
        )

    await ctx.respond("Persona cleared.", ephemeral=True)


@bot.event
async def on_message(message: Message):
    global account_data

    if bot.user is None or message.interaction is not None:
        return

    mention_of_bot = bot.user.mentioned_in(message)

    reply_to_bot = (
        message.reference
        and message.reference.resolved
        and not isinstance(message.reference.resolved, DeletedReferencedMessage)
        and message.reference.resolved.author == bot.user
    )

    dm_to_bot = isinstance(message.channel, discord.DMChannel)

    if mention_of_bot or reply_to_bot or dm_to_bot:
        reply = await message.reply("Thinking...")

        with db.atomic():
            settings = (
                SettingsDict(
                    **model_to_dict(
                        Settings.get_or_create(
                            guild=str(message.guild.id),
                        )[0]
                    )
                )
                if message.guild
                else DEFAULT_SETTINGS
            )

        chat = []
        referenced = message
        for _ in range(settings["context_message_count"]):
            if referenced.reference and referenced.reference.message_id:
                referenced = await message.channel.fetch_message(
                    referenced.reference.message_id
                )
                if referenced is None or isinstance(
                    referenced, DeletedReferencedMessage
                ):
                    break

                answer = referenced.content

                if referenced.reference and referenced.reference.message_id:
                    referenced = await message.channel.fetch_message(
                        referenced.reference.message_id
                    )
                    if referenced is None or isinstance(
                        referenced, DeletedReferencedMessage
                    ):
                        break

                    question = referenced.content

                    chat.insert(
                        0, dict(question=re.sub(r"<@.*?>", "", question), answer=answer)
                    )
                else:
                    break

        response = you.Completion.create(
            prompt=settings["persona"] + re.sub(r"<@.*?>", "", message.content),
            chat=chat,
        )

        if response is None or response.text is None:
            await reply.edit(content="Failed to generate response.")
            return

        reply = await reply.edit(
            content=(reply.content + response.text)
            if reply.content != "Thinking..."
            else response.text
        )


bot.run(getenv("TOKEN"))
