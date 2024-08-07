import asyncio
import os
import shutil
import logging
from telethon import TelegramClient, functions, types
from telethon.errors import TimeoutError, InviteHashExpiredError, ChannelPrivateError, ChatAdminRequiredError, InviteHashInvalidError
from telethon.tl.types import InputMessagesFilterPhotos, InputMessagesFilterDocument, InputMessagesFilterVideo
from telethon.tl.functions.messages import ImportChatInviteRequest, GetHistoryRequest, DeleteMessagesRequest, DeleteChatUserRequest, SendMessageRequest
import discord
from discord.ext import commands
from moviepy.video.io.ffmpeg_tools import ffmpeg_extract_subclip
from moviepy.video.io.VideoFileClip import VideoFileClip
import psutil
import platform
from datetime import datetime, timedelta
import random

api_id = 
api_hash = ''
telegram_client = TelegramClient('', api_id, api_hash)

discord_token = ''

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

logging.basicConfig(
    level=logging.INFO,
    format="(%(asctime)s) [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)

async def send_file_to_discord(file_path, thread):
    await thread.send(file=discord.File(file_path))

def get_random_color():
    return discord.Color(random.randint(0, 0xFFFFFF))

def split_video(file_path, target_size_mb=48):
    video = VideoFileClip(file_path)
    total_duration = video.duration

    total_size_bytes = os.path.getsize(file_path)
    bitrate = (total_size_bytes * 8) / total_duration
    target_size_bytes = target_size_mb * 1024 * 1024
    target_duration = (target_size_bytes * 8) / bitrate

    current_start = 0
    parts = []
    part_index = 0

    while current_start < total_duration:
        current_end = min(total_duration, current_start + target_duration)
        part_path = f"{file_path}_part{part_index}.mp4"

        try:
            ffmpeg_extract_subclip(file_path, current_start, current_end, targetname=part_path)
            parts.append(part_path)
            print(f"Đang chia thành đoạn thứ {part_index} từ phân cảnh {current_start} đến {current_end}")
            current_start = current_end
            part_index += 1
        except Exception as e:
            print(f"Đã xảy ra lỗi khi tách file video: {e}")
            break

    if video.reader:
        video.reader.close()
    if video.audio and video.audio.reader:
        video.audio.reader.close_proc()

    return parts

async def download_file(media, filename, retries=10):
    for attempt in range(retries):
        try:
            await telegram_client.download_media(media, filename)
            return filename
        except TimeoutError:
            print(f"Lỗi TimeOut: Thử lại lần thứ {attempt + 1}/{retries}")
            if attempt + 1 == retries:
                raise
            await asyncio.sleep(5)

async def join_group_or_channel(telegram_channel):
    async with telegram_client:
        try:
            if "t.me/joinchat" in telegram_channel or "t.me/+" in telegram_channel:
                invite_hash = telegram_channel.split('/')[-1].replace('+', '')
                try:
                    updates = await telegram_client(ImportChatInviteRequest(invite_hash))
                    entity = updates.chats[0] if updates.chats else updates.users[0]
                    print(f"Đã tham gia vào nhóm/kênh: {telegram_channel}")
                except InviteHashExpiredError:
                    print(f"Link mời này đã hết hạn hoặc không hợp lệ: {telegram_channel}")
                    return None
                except InviteHashInvalidError:
                    print(f"Mã lời mời không hợp lệ: {telegram_channel}")
                    return None
                except Exception as e:
                    if 'already a participant' in str(e):
                        print(f"Người dùng đã tham gia vào nhóm/kênh: {telegram_channel}")
                        return 'already_a_participant'
                    print(f"Lỗi khi tham gia vào nhóm/kênh: {e}")
                    return None
            else:
                entity = await telegram_client.get_entity(telegram_channel)
                if isinstance(entity, types.Channel):
                    await telegram_client(functions.channels.JoinChannelRequest(channel=entity))
                    print(f"Đã tham gia vào kênh: {telegram_channel}")
                elif isinstance(entity, (types.User, types.Chat)):
                    print(f"Đã tìm thấy người dùng hoặc bot: {telegram_channel}")
                else:
                    print(f"Loại thực thể không xác định: {telegram_channel}")
                    return None
            return entity
        except (ChannelPrivateError, ChatAdminRequiredError, ValueError) as e:
            print(f"Lỗi khi tham gia vào kênh này: {e}")
            return None
        except Exception as e:
            print(f"Lỗi không xác định khi tham gia vào kênh/nhóm: {e}")
            return None

async def download_and_send_messages(thread, telegram_channel):
    entity = await join_group_or_channel(telegram_channel)
    if entity == 'already_a_participant':
        await thread.send("**<a:zerotwo:1149986532678189097> Lỗi: Nhóm / Kênh đã được tham gia trước đó, vui lòng dùng `/leave` để rời nhóm / kênh**")
        return
    if not entity:
        await thread.send("**<a:zerotwo:1149986532678189097> Đã xảy ra lỗi khi tham gia vào nhóm / kênh Telegram. Xin hãy cung cấp 1 Link lời mời hợp lệ!**")
        return

    invite_id = telegram_channel.split('/')[-1]
    work_dir = f'./telegram_{invite_id}'
    os.makedirs(work_dir, exist_ok=True)

    async with telegram_client:
        if isinstance(entity, types.User) and entity.bot:
            print('=== Bắt đầu tải tin nhắn từ bot Telegram! ===')
            history = await telegram_client(GetHistoryRequest(
                peer=entity,
                limit=1000,
                offset_date=None,
                offset_id=0,
                max_id=0,
                min_id=0,
                add_offset=0,
                hash=0
            ))
            messages = history.messages
        else:
            print('=== Bắt đầu tải nội dung từ Telegram! ===')
            messages = await telegram_client.get_messages(entity, limit=None)

        total_messages = len(messages)
        for index, message in enumerate(messages, start=1):
            if message.photo:
                filename = f"{work_dir}/{message.id}.jpg"
                print(f"Đang tải ảnh: {index} / {total_messages} | Tên tệp: {filename}")
                await download_file(message.photo, filename)
                await send_file_to_discord(filename, thread)
            elif message.video:
                filename = f"{work_dir}/{message.id}.mp4"
                print(f"Đang tải video: {index} / {total_messages} | Tên tệp: {filename}")
                await download_file(message.video, filename)
                if os.path.getsize(filename) > 50 * 1024 * 1024:
                    parts = split_video(filename)
                    for part in parts:
                        await send_file_to_discord(part, thread)
                        os.remove(part)
                else:
                    await send_file_to_discord(filename, thread)
            elif message.document:
                file_name = None
                for attribute in message.document.attributes:
                    if isinstance(attribute, types.DocumentAttributeFilename):
                        file_name = attribute.file_name
                        break
                if not file_name:
                    file_name = f"{message.id}"
                filename = f"{work_dir}/{file_name}"
                print(f"Đang tải tệp: {file_name}")
                await download_file(message.document, filename)
                await send_file_to_discord(filename, thread)
            else:
                print(f"Đã bỏ qua tin nhắn: {message.id} (không có nội dung hỗ trợ)")

    shutil.rmtree(work_dir)
    print(f'Đã xóa thư mục: "{work_dir}"')

async def leave_group_or_delete_messages(telegram_channel):
    async with telegram_client:
        try:
            entity = await telegram_client.get_entity(telegram_channel)
            if isinstance(entity, types.Channel):
                await telegram_client(functions.channels.LeaveChannelRequest(channel=entity))
                print(f"Đã rời khỏi kênh: {telegram_channel}")
                return "Đã rời khỏi kênh Telegram thành công!"
            elif isinstance(entity, types.User):
                print(f"Đã tìm thấy người dùng hoặc bot: {telegram_channel}")
                messages = await telegram_client.get_messages(entity, limit=None)
                message_ids = [msg.id for msg in messages]
                await telegram_client(DeleteMessagesRequest(id=message_ids))
                print(f"Đã xóa tất cả tin nhắn từ người dùng hoặc bot: {telegram_channel}")
                return "Đã xóa tất cả tin nhắn từ người dùng / Bot thành công!"
            elif isinstance(entity, types.Chat):
                await telegram_client(DeleteChatUserRequest(chat_id=entity.id, user_id=telegram_client.get_me().id))
                print(f"Đã rời khỏi nhóm: {telegram_channel}")
                return "Đã rời khỏi nhóm Telegram thành công!"
            else:
                print(f"Loại thực thể không xác định: {telegram_channel}")
                return "Link Telegram này không xác định!"
        except (ChannelPrivateError, ChatAdminRequiredError, ValueError) as e:
            print(f"Lỗi khi rời khỏi kênh/nhóm này hoặc xóa tin nhắn: {e}")
            return f"Lỗi khi rời khỏi kênh / nhóm Telegram hoặc xóa tin nhắn Telegram: {e}"

@bot.slash_command(description="Tải nội dung từ Telegram và gửi vào chủ đề Discord ?")
async def crawl(ctx, discord_thread_id: discord.Option(str, description="Nhập ID chủ đề Discord vào đây!"), telegram_channel: discord.Option(str, description="Nhập Link mời từ Telegram vào đây!")):
    await ctx.defer()
    try:
        await ctx.send_followup(f"**<a:sip:1149986505964662815> Bắt đầu tải dữ liệu từ `{telegram_channel}` vào chủ đề <#{discord_thread_id}>**")
        thread = bot.get_channel(int(discord_thread_id))
        if thread is None:
            await ctx.send_followup(f'**<a:zerotwo:1149986532678189097> Không thể tìm thấy chủ đề với ID: `{discord_thread_id}` trên Discord!**')
            return
        if thread.last_message and thread.last_message.content == "**<a:zerotwo:1149986532678189097> Lỗi: Nhóm / Kênh đã được tham gia trước đó, vui lòng dùng `/leave` để rời nhóm / kênh**":
            await ctx.send_followup(f"**<a:zerotwo:1149986532678189097> Đã xảy ra lỗi ngoài ý muốn! Vui lòng kiểm tra lỗi tại <#{discord_thread_id}>!**")
        else:
            await download_and_send_messages(thread, telegram_channel)
            await ctx.send_followup(f"**<a:emoji_anime:1149986363802918922> Đã thực thi xong câu lệnh! Xin hãy kiểm tra tại: <#{discord_thread_id}>!**")
    except Exception as e:
        await ctx.send_followup(f"**<a:zerotwo:1149986532678189097> Đã xảy ra lỗi ngoài ý muốn: {e}**")

@bot.slash_command(description="Rời khỏi kênh / nhóm Telegram hoặc xóa tất cả tin nhắn từ người dùng / Bot Telegram ?")
async def leave(ctx, telegram_channel: discord.Option(str, description="Nhập Link từ Telegram vào đây!")):
    await ctx.defer()
    try:
        result = await leave_group_or_delete_messages(telegram_channel)
        await ctx.send_followup(f"**<a:zerotwo:1149986532678189097> {result}**")
    except Exception as e:
        await ctx.send_followup(f"**<a:zerotwo:1149986532678189097> Đã xảy ra lỗi ngoài ý muốn: {e}**")

@bot.slash_command(description="Kiểm tra thông tin máy chủ ?")
async def ping(ctx):
    await ctx.defer()

    cpu_usage = psutil.cpu_percent()
    cpu_name = platform.processor()
    ram = psutil.virtual_memory()
    ram_usage = ram.percent
    used_ram = round(ram.used / (1024 ** 3), 2)
    total_ram = round(ram.total / (1024 ** 3), 2) 
    disk = psutil.disk_usage('/')
    disk_usage = disk.percent
    used_disk = round(disk.used / (1024 ** 3), 2)
    total_disk = round(disk.total / (1024 ** 3), 2)
    python_version = platform.python_version()
    latency = round(bot.latency * 1000)
    current_time = datetime.now()
    uptime = current_time - bot.uptime
    uptime_str = str(timedelta(seconds=uptime.total_seconds()))

    embed = discord.Embed(title="Cấu hình PC của bé nô lệ !???", color=get_random_color())
    embed.add_field(name="Độ trễ của bé", value=f"{latency} ms", inline=True)
    embed.add_field(name="Tên / Sử dụng CPU", value=f"{cpu_name} ({cpu_usage}%)", inline=True)
    embed.add_field(name="Sử dụng RAM", value=f"{used_ram} GB ({ram_usage}%)", inline=True)
    embed.add_field(name="Sử dụng ổ đĩa", value=f"{used_disk} GB ({disk_usage}%)", inline=True)
    embed.add_field(name="Phiên bản Python", value=python_version, inline=True)
    embed.add_field(name="Uptime", value=uptime_str, inline=True)
    embed.set_image(url="https://raw.githubusercontent.com/dragonx943/listcaidaubuoi/main/campFire.gif")

    await ctx.send_followup(embed=embed)

@bot.event
async def on_ready():
    if not hasattr(bot, 'uptime'):
        bot.uptime = datetime.now()
    activity=discord.Activity(type=discord.ActivityType.playing, name="Telegram Desktop", state="Bạn đọc dòng này làm gì? Bạn thích tôi à?")
    await bot.change_presence(status=discord.Status.dnd, activity=activity)
    print(f'Đã đăng nhập với Bot: {bot.user}')

bot.run(discord_token)
