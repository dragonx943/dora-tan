import asyncio
import os
from telethon import TelegramClient, utils
from telethon.errors import TimeoutError
from telethon.tl.types import InputMessagesFilterPhotos, InputMessagesFilterDocument, InputMessagesFilterVideo
import discord
from discord.ext import commands
from moviepy.video.io.ffmpeg_tools import ffmpeg_extract_subclip
from moviepy.video.io.VideoFileClip import VideoFileClip

api_id = 
api_hash = ''
telegram_client = TelegramClient('', api_id, api_hash)
telegram_channel = ''

discord_token = ''
discord_thread_id = ''

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

async def send_file_to_discord(file_path, thread):
    await thread.send(file=discord.File(file_path))

def split_video(file_path, segment_duration=120):
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
            print(f"Đang chia thành đoạn thứ {part_index} từ phân cảnh {current_start} đến {current_end}...")
            current_start = current_end
            part_index += 1
        except Exception as e:
            print(f"Đã xảy ra sự cố khi tách file video dài: {e}")
            break

    video.close()
    return parts

async def download_file(media, filename, retries=5):
    for attempt in range(retries):
        try:
            await telegram_client.download_media(media, filename)
            return filename
        except TimeoutError:
            print(f"Lỗi timeout: Đang thử lại lần thứ {attempt + 1}/{retries}")
            if attempt + 1 == retries:
                raise
            await asyncio.sleep(5)

async def download_and_send_messages(thread):
    async with telegram_client:
        print('=== Bắt đầu tải hình ảnh từ Telegram! ===')
        photos = await telegram_client.get_messages(telegram_channel, None, filter=InputMessagesFilterPhotos)
        total_photos = len(photos)
        for index, photo in enumerate(photos, start=1):
            filename = f"./telegram/{photo.id}.jpg"
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
                await download_file(file, f"./telegram/{file_name}")
                await send_file_to_discord(f"./telegram/{file_name}", thread)
            except Exception as e:
                print(f"Đã xảy ra lỗi khi tải về file: {file_name}: {e}")
        
        print('=== Bắt đầu tải Video từ Telegram! ===')
        videos = await telegram_client.get_messages(telegram_channel, None, filter=InputMessagesFilterVideo)
        total_videos = len(videos)
        for index, video in enumerate(videos, start=1):
            filename = f"./telegram/{video.id}.mp4"
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

@bot.event
async def on_ready():
    print(f'Đã đăng nhập với Bot: {bot.user}')
    thread = bot.get_channel(int(discord_thread_id))
    if thread is None:
        print(f'Không thể tìm thấy chủ đề với ID: {discord_thread_id} trên Discord!')
    else:
        await download_and_send_messages(thread)

if not os.path.exists('./telegram/'):
    os.makedirs('./telegram/')

bot.run(discord_token)
