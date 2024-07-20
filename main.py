import asyncio
import os
from telethon import TelegramClient, utils
from telethon.tl.types import InputMessagesFilterPhotos, InputMessagesFilterDocument, InputMessagesFilterVideo
import discord
import moviepy
from discord.ext import commands

api_id = 
api_hash = ''
telegram_client = TelegramClient('', api_id, api_hash)
telegram_channel = '' # Ví dụ: https://t.me/douban_read

discord_token = ''
discord_thread_id = ''

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

async def send_file_to_discord(file_path, thread):
    await thread.send(file=discord.File(file_path))

def split_video(file_path, max_size_mb=50):
    from moviepy.video.io.VideoFileClip import VideoFileClip

    video = VideoFileClip(file_path)
    total_duration = int(video.duration)
    max_size_bytes = max_size_mb * 512 * 512
    current_start = 0
    parts = []
    part_index = 0

    while current_start < total_duration:
        current_end = total_duration
        part_path = f"{file_path}_part{part_index}.mp4"

        while current_end > current_start:
            ffmpeg_extract_subclip(file_path, current_start, current_end, targetname=part_path)
            if os.path.getsize(part_path) <= max_size_bytes:
                parts.append(part_path)
                current_start = current_end
                part_index += 1
                break
            else:
                current_end -= 10

        if current_end <= current_start:
            print("Đã xảy ra lỗi khi chia nhỏ file Video từ Telegram!")
            break

    return parts

async def download_and_send_messages(thread):
    async with telegram_client:
        print('=== Bắt đầu tải hình ảnh từ Telegram! ===')
        photos = await telegram_client.get_messages(telegram_channel, None, filter=InputMessagesFilterPhotos)
        total_photos = len(photos)
        for index, photo in enumerate(photos, start=1):
            filename = f"./telegram/{photo.id}.jpg"
            print(f"Đang tải: {index} / {total_photos} ảnh | Tên tệp: {filename}")
            await telegram_client.download_media(photo, filename)
            await send_file_to_discord(filename, thread)
          
        print('=== Bắt đầu tải file phương tiện từ Telegram! ===')
        files = await telegram_client.get_messages(telegram_channel, None, filter=InputMessagesFilterDocument)
        for file in files:
            attributes = file.media.document.attributes
            file_name = attributes[0].file_name if len(attributes) == 1 else attributes[1].file_name
            print(f"Đang tải tệp: {file_name}")
            try:
                await asyncio.wait_for(telegram_client.download_media(file, f"./telegram/{file_name}"), timeout=120)
                await send_file_to_discord(f"./telegram/{file_name}", thread)
            except asyncio.TimeoutError:
                print(f"Đã hết thời gian chờ khi tải file: {file_name}")
            except Exception as e:
                print(f"Đã xảy ra lỗi khi tải về file: {file_name}: {e}")
        
        print('=== Bắt đầu tải Video từ Telegram! ===')
        videos = await telegram_client.get_messages(telegram_channel, None, filter=InputMessagesFilterVideo)
        total_videos = len(videos)
        for index, video in enumerate(videos, start=1):
            filename = f"./telegram/{video.id}.mp4"
            print(f"Đang tải về: {index} / {total_videos} videos | Tên tệp: {filename}")
            try:
                await asyncio.wait_for(telegram_client.download_media(video, filename))
                if os.path.getsize(filename) > 100 * 512 * 512:
                    parts = split_video(filename)
                    for part in parts:
                        await send_file_to_discord(part, thread)
                        os.remove(part)
                else:
                    await send_file_to_discord(filename, thread)
            except asyncio.TimeoutError:
                print(f"Đã quá thời gian chờ để tải về file: {filename}")
            except Exception as e:
                print(f"Đã xảy ra lỗi khi tải: {filename}: {e}")

@bot.event
async def on_ready():
    print(f'Đã đăng nhập với Bot: {bot.user}')
    thread = bot.get_channel(int(discord_thread_id))
    if thread is None:
        print(f'Không thể tìm thấy chủ đề với ID: {discord_thread_id} trên Discord!')
        break
    else:
        await download_and_send_messages(thread)
        break

if not os.path.exists('./telegram/'):
    os.makedirs('./telegram/')

# Run the Discord bot
bot.run(discord_token)
