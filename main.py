import asyncio
import os
import shutil
import logging
from telethon import TelegramClient, functions
from telethon.errors import TimeoutError, InviteHashExpiredError, ChannelPrivateError, ChatAdminRequiredError, InviteHashInvalidError
from telethon.tl.types import InputMessagesFilterPhotos, InputMessagesFilterDocument, InputMessagesFilterVideo
from telethon.tl.functions.messages import ImportChatInviteRequest
import discord
from discord.ext import commands
from moviepy.video.io.ffmpeg_tools import ffmpeg_extract_subclip
from moviepy.video.io.VideoFileClip import VideoFileClip

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

def split_video(file_path, segment_duration=60):
    video = VideoFileClip(file_path)
    total_duration = int(video.duration)
    current_start = 0
    parts = []
    part_index = 0

    while current_start < total_duration:
        current_end = min(total_duration, current_start + segment_duration)
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

    video.close()
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
        if "t.me/joinchat" in telegram_channel or "t.me/+" in telegram_channel:
            try:
                invite_code = telegram_channel.split('/')[-1][1:]
                await telegram_client(ImportChatInviteRequest(invite_code))
            except InviteHashExpiredError:
                print("Link mời đã bị lỗi / hết hạn!")
                return False
        else:
            try:
                await telegram_client(functions.channels.JoinChannelRequest(channel=telegram_channel.split('/')[-1]))
                print(f"Đã tham gia vào kênh: {telegram_channel}")
            except (ChannelPrivateError, ChatAdminRequiredError):
                print("Lỗi khi tham gia vào kênh này, có thể là do kênh private hoặc cần sự ủy quyền từ Admin.")
                return False
        return True

async def download_and_send_messages(thread, telegram_channel):
    joined = await join_group_or_channel(telegram_channel)
    if not joined:
        await thread.send("Lỗi khi tham gia vào nhóm / kênh Telegram. Xin hãy cung cấp 1 Link lời mời hợp lệ!")
        return

    invite_id = telegram_channel.split('/')[-1]
    work_dir = f'./telegram_{invite_id}'
    os.makedirs(work_dir, exist_ok=True)

    async with telegram_client:
        print('=== Bắt đầu tải hình ảnh từ Telegram! ===')
        photos = await telegram_client.get_messages(telegram_channel, None, filter=InputMessagesFilterPhotos)
        total_photos = len(photos)
        for index, photo in enumerate(photos, start=1):
            filename = f"{work_dir}/{photo.id}.jpg"
            print(f"Đang tải: {index} / {total_photos} ảnh | Tên tệp: {filename}")
            await download_file(photo, filename)
            await send_file_to_discord(filename, thread)
          
        print('=== Bắt đầu tải file phương tiện từ Telegram! ===')
        files = await telegram_client.get_messages(telegram_channel, None, filter=InputMessagesFilterDocument)
        for file in files:
            attributes = file.media.document.attributes
            file_name = attributes[0].file_name if len(attributes) == 1 else attributes[1].file_name
            print(f"Đang tải tệp: {file_name}")
            try:
                await download_file(file, f"{work_dir}/{file_name}")
                await send_file_to_discord(f"{work_dir}/{file_name}", thread)
            except Exception as e:
                print(f"Đã xảy ra lỗi khi tải về file: {file_name}: {e}")
        
        print('=== Bắt đầu tải Video từ Telegram! ===')
        videos = await telegram_client.get_messages(telegram_channel, None, filter=InputMessagesFilterVideo)
        total_videos = len(videos)
        for index, video in enumerate(videos, start=1):
            filename = f"{work_dir}/{video.id}.mp4"
            print(f"Đang tải về: {index} / {total_videos} videos | Tên tệp: {filename}")
            try:
                await download_file(video, filename)
                if os.path.getsize(filename) > 50 * 1024 * 1024:
                    parts = split_video(filename)
                    for part in parts:
                        await send_file_to_discord(part, thread)
                        os.remove(part)
                else:
                    await send_file_to_discord(filename, thread)
            except Exception as e:
                print(f"Đã xảy ra lỗi khi tải: {filename}: {e}")

    shutil.rmtree(work_dir)
    print(f'Đã xóa thư mục "{work_dir}"')

@bot.slash_command(description="Tải nội dung từ Telegram và gửi vào chủ đề Discord")
async def crawl(ctx, discord_thread_id: discord.Option(str, description="Nhập ID chủ đề Discord vào đây!"), telegram_channel: discord.Option(str, description="Nhập Link mời từ Telegram vào đây!")):
    await ctx.defer()
    try:
        await ctx.send_followup(f"**<a:sip:1149986505964662815> Bắt đầu tải dữ liệu từ `{telegram_channel}` vào chủ đề <#{discord_thread_id}>**")
        thread = bot.get_channel(int(discord_thread_id))
        if thread is None:
            await ctx.send_followup(f'**<a:zerotwo:1149986532678189097> Không thể tìm thấy chủ đề với ID: `{discord_thread_id}` trên Discord!**')
        else:
            await download_and_send_messages(thread, telegram_channel)
            await ctx.send_followup(f"**<a:emoji_anime:1149986363802918922> Đã hoàn tất tải từ `{telegram_channel}` vào chủ đề <#{discord_thread_id}>**")
    except Exception as e:
        await ctx.send_followup(f"**<a:zerotwo:1149986532678189097> Đã xảy ra lỗi ngoài ý muốn: {e}**")

@bot.event
async def on_ready():
    activity=discord.Activity(type=discord.ActivityType.playing, name="Telegram Desktop", state="Bạn đọc dòng này làm gì? Bạn thích tôi à?")
    await bot.change_presence(status=discord.Status.dnd, activity=activity)
    print(f'Đã đăng nhập với Bot: {bot.user}')

bot.run(discord_token)
