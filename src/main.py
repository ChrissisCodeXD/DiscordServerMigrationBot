import hikari
import lightbulb
from hikari.undefined import UNDEFINED
from dotenv import load_dotenv
import os
OLD_GUILD = 00000000000000000 #old guild discord id
NEW_GUILD = 1134124760595431445 #new guild discord id
ONLY_PURGE = False #if you want to only purge the new guild
EXCLUDE_CATEGORYS = [ #ids of categorys you want to not copy their channels
    1112366737715888188,
    1112428257019699250
]
load_dotenv()
bot = lightbulb.BotApp(token=os.getenv("TOKEN"), intents=hikari.Intents.ALL)

def get_category_channels(guild: hikari.RESTGuild):
    channels = guild.get_channels()
    for channel in channels:
        channel: hikari.PermissibleGuildChannel = channels[channel]
        if channel.type == hikari.ChannelType.GUILD_CATEGORY:
            yield channel

old_parent_to_new_parent = {}
old_role_to_new_role = {}




@bot.listen(hikari.StartedEvent)
async def on_start(event: hikari.StartedEvent) -> None:
    old_guild = await event.app.rest.fetch_guild(OLD_GUILD)
    new_guild = await event.app.rest.fetch_guild(NEW_GUILD)

    for role in new_guild.get_roles():
        role = new_guild.get_role(role)
        if role.id == new_guild.id or role.bot_id or role.is_premium_subscriber_role: continue
        try:
            await bot.rest.delete_role(new_guild.id, role.id)
            print(f"Deleted role {role.name}")
        except hikari.ForbiddenError:
            print(f"Failed to delete role {role.name}")
    for channel in new_guild.get_channels():
        channel = new_guild.get_channel(channel)
        await channel.delete()
        print(f"Deleted channel {channel.name}")
    for emoji in new_guild.get_emojis():
        emoji = new_guild.get_emoji(emoji)
        await bot.rest.delete_emoji(new_guild.id, emoji.id)
        print(f"Deleted emoji {emoji.name}")
    if ONLY_PURGE: return
    await new_guild.edit(
        name=old_guild.name,
        icon=old_guild.make_icon_url(),
        banner=old_guild.make_banner_url(),
        splash=old_guild.make_splash_url(),
        verification_level=old_guild.verification_level,
        default_message_notifications=old_guild.default_message_notifications,
        afk_timeout=old_guild.afk_timeout,
        preferred_locale=old_guild.preferred_locale,
    )
    print("Edited guild")

    for emoji in old_guild.get_emojis():
        emoji = old_guild.get_emoji(emoji)
        try:
            await bot.rest.create_emoji(
                new_guild.id,
                name=emoji.name,
                image=emoji.url,
            )
        except Exception as e:
            print(f"Failed to create emoji {emoji.name} with error {e}")

    for role in old_guild.get_roles():
        role = old_guild.get_role(role)
        if not role: continue
        if role.id == old_guild.id or role.bot_id: continue
        try:
            try:
                icon = role.make_icon_url() or UNDEFINED
                new_role = await bot.rest.create_role(
                    new_guild.id,
                    name=role.name,
                    permissions=role.permissions,
                    color=role.color,
                    hoist=role.is_hoisted,
                    icon=icon,
                    mentionable=role.is_mentionable,
                )
                print(f"Created role {role.name} with icon")
                old_role_to_new_role[role.id] = new_role.id

            except hikari.ForbiddenError as e:
                if e.message.startswith("This server needs more boosts to perform this action"):
                    new_role = await bot.rest.create_role(
                        new_guild.id,
                        name=role.name,
                        permissions=role.permissions,
                        color=role.color,
                        hoist=role.is_hoisted,
                        mentionable=role.is_mentionable,
                    )
                    print(f"Created role {role.name}")
                    old_role_to_new_role[role.id] = new_role.id
        except Exception as e:
            print(f"Failed to create role {role.name} with error {e}")


    for category in get_category_channels(old_guild):
        try:
            new_category = await new_guild.create_category(
                name=category.name,
                reason="Migration"
            )
            old_parent_to_new_parent[
                category.id
            ] = new_category.id
            print(f"Created category {category.name}")
        except Exception as e:
            print(f"Failed to create category {category.name} with error {e}")

    for channel in old_guild.get_channels():
        channel = old_guild.get_channel(channel)
        if channel.type == hikari.ChannelType.GUILD_CATEGORY: continue
        try:
            category = old_parent_to_new_parent.get(channel.parent_id, UNDEFINED)
            exclude = False
            for c in EXCLUDE_CATEGORYS:
                if channel.parent_id and int(channel.parent_id) == c:
                    exclude = True
            if exclude: continue
            if channel.type == hikari.ChannelType.GUILD_VOICE:
                await new_guild.create_voice_channel(
                    name=channel.name,
                    category=category,
                    bitrate=channel.bitrate,
                    user_limit=channel.user_limit,
                    reason="Migration"
                )
            if channel.type == hikari.ChannelType.GUILD_TEXT:
                await new_guild.create_text_channel(
                    name=channel.name,
                    category=category,
                    topic=channel.topic,
                    nsfw=channel.is_nsfw,
                    reason="Migration"
                )
        except Exception as e:
            print(f"Failed to create channel {channel.name} with error {e}")

    exit(0)

bot.run()
