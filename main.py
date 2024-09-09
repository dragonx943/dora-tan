import asyncio
import re
import os
import shutil
import logging
import aiohttp
import subprocess
from pathlib import Path
from hydrogram import Client, filters
from hydrogram.types import Message
from telethon.errors import FloodWaitError
from hydrogram.errors import UserAlreadyParticipant, InviteHashExpired, InviteHashInvalid, UsernameInvalid, UsernameNotOccupied, FloodWait
import discord
from discord import File
from discord import Embed
from discord import Attachment
from discord.ext import commands
from discord.ui import Select, View
from moviepy.editor import VideoFileClip
from moviepy.video.io.ffmpeg_tools import ffmpeg_extract_subclip
from moviepy.video.io.VideoFileClip import VideoFileClip
from selenium import webdriver
from selenium.webdriver.common.by import By
import psutil
import platform
from datetime import datetime, timedelta
import random
import time
import json
import pytz
import urllib.parse
import zipfile
import io
import json
import yt_dlp
import requests
import win32file
from tqdm import tqdm
from unidecode import unidecode
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

last_add_timestamp = None
last_steam_usage = {}
BOT_OWNER_ID = 
steam_role= 
required_server_id = 
required_role_id = 
api_id = 
api_hash = ''
phone_number = ''
telegram_client = Client("", api_id=api_id, api_hash=api_hash, phone_number=phone_number)

discord_token = ''

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='#', intents=intents)

logging.basicConfig(
    level=logging.INFO,
    format="(%(asctime)s) [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger()
handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)

async def send_file_to_discord(file_path, thread):
    await thread.send(file=discord.File(file_path))

def get_long_path_name(path):
    try:
        return win32file.GetLongPathName(path)
    except:
        return path

def safe_path(path):
    parts = path.split(os.path.sep)
    safe_parts = []
    for part in parts:
        safe = unidecode(''.join(c if c.isalnum() or c in ['-', '_', '.', ' ', ':'] else '_' for c in part)).strip()
        safe_parts.append(safe)
    return os.path.sep.join(safe_parts)

def normalize_path(path):
    return str(Path(path).resolve())

def list_files_recursively(directory):
    for root, dirs, files in os.walk(directory):
        for file in files:
            yield normalize_path(os.path.join(root, file))

def list_all_files(directory):
    all_files = []
    for root, dirs, files in os.walk(directory):
        for file in files:
            all_files.append(os.path.join(root, file))
    return all_files

def safe_extract(zip_ref, temp_dir):
    for file in zip_ref.namelist():
        try:
            safe_path_name = safe_path(file.rstrip())
            safe_full_path = os.path.normpath(os.path.join(temp_dir, safe_path_name))
            
            os.makedirs(os.path.dirname(safe_full_path), exist_ok=True)
            
            if not file.endswith('/'):
                source = zip_ref.open(file)
                target = open(safe_full_path, "wb")
                with source, target:
                    shutil.copyfileobj(source, target)
            
            print(f"Đã giải nén: {safe_full_path}")
        except Exception as e:
            print(f"Lỗi khi giải nén {file}: {str(e)}")
    
    for root, dirs, files in os.walk(temp_dir, topdown=False):
        for name in files + dirs:
            original_path = os.path.join(root, name)
            safe_name = safe_path(name)
            safe_path_full = os.path.join(root, safe_name)
            if original_path != safe_path_full:
                try:
                    os.rename(original_path, safe_path_full)
                    print(f"Đã đổi tên: {original_path} -> {safe_path_full}")
                except Exception as e:
                    print(f"Lỗi khi đổi tên {original_path}: {str(e)}")

def get_random_color():
    return discord.Color(random.randint(0, 0xFFFFFF))

async def download_file_with_retry(url, local_filename, max_retries=10000):
    for attempt in range(max_retries):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    response.raise_for_status()
                    total_size = int(response.headers.get('content-length', 0))
                    
                    with open(local_filename, 'wb') as f, tqdm(
                        desc=local_filename,
                        total=total_size,
                        unit='iB',
                        unit_scale=True,
                        unit_divisor=1024,
                    ) as progress_bar:
                        chunk_size = 8192
                        async for chunk in response.content.iter_chunked(chunk_size):
                            size = f.write(chunk)
                            progress_bar.update(size)
            
            return local_filename
        except aiohttp.ClientError as e:
            print(f"Lỗi khi tải file (lần thử {attempt + 1}/{max_retries}): {e}")
            if attempt + 1 < max_retries:
                await asyncio.sleep(5)
            else:
                raise
        except Exception as e:
            print(f"Lỗi khi tải file: {e}. Thử lại lần thứ {attempt + 1}/{max_retries}")
            if attempt + 1 == max_retries:
                raise
    return local_filename

def init_driver():
    options = webdriver.FirefoxOptions()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    driver = webdriver.Firefox(options=options)
    return driver

def check_cookie_validity(cookie_path):
    with open(cookie_path, 'r') as file:
        cookies = json.load(file)
    
    session = requests.Session()
    retry = Retry(total=5, backoff_factor=0.1, status_forcelist=[500, 502, 503, 504])
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)

    for cookie in cookies:
        session.cookies.set(cookie['name'], cookie['value'], domain=cookie['domain'], path=cookie['path'])

    response = session.get("https://www.netflix.com/browse")
    if "profiles" in response.text:
        return True
    return False

def load_cookies(driver, cookie_file):
    with open(cookie_file, "r") as file:
        cookies = json.load(file)
        for cookie in cookies:
            if 'expiry' in cookie:
                try:
                    cookie['expiry'] = int(cookie['expiry'])
                except (ValueError, TypeError):
                    del cookie['expiry']
            if 'sameSite' in cookie:
                del cookie['sameSite']
            driver.add_cookie(cookie)

def login_netflix(driver, type, code, cookie_file):
    url = f"https://www.netflix.com/{type}"
    driver.get(url)
    time.sleep(2)
    load_cookies(driver, cookie_file)
    driver.refresh()
    time.sleep(2)
    pin_inputs = driver.find_elements(By.CLASS_NAME, 'pin-number-input')
    code_digits = list(code.replace('-', ''))
    for i in range(min(len(pin_inputs), len(code_digits))):
        pin_inputs[i].send_keys(code_digits[i])
    submit_button = driver.find_element(By.CSS_SELECTOR, '.tvsignup-continue-button')
    if submit_button.is_enabled():
        submit_button.click()
    else:
        raise Exception("Nút gửi bị vô hiệu hóa.")
    time.sleep(5)

def convert_cookies_to_json_from_content(file_content):
    cookies = []
    for line in file_content.splitlines():
        if not line.startswith('#') and line.strip():
            parts = line.split('\t')
            if len(parts) >= 7:
                cookie = {
                    'domain': parts[0],
                    'httpOnly': 'HttpOnly' in parts[0],
                    'path': parts[2],
                    'secure': parts[3].lower() == 'true',
                    'expiry': int(parts[4]) if parts[4] != "0" else None,
                    'name': parts[5],
                    'value': parts[6].strip()
                }
                if cookie['expiry'] is None:
                    del cookie['expiry']
                cookies.append(cookie)
    return cookies

def split_video(file_path, target_size_mb=40):
    target_size_bytes = target_size_mb * 1024 * 1024
    temp_output_template = f"{file_path}_temp%03d.mp4"
    final_output_template = f"{file_path}_part%03d.mp4"

    if not os.access(file_path, os.R_OK):
        print(f"Không có quyền đọc file: {file_path}")
        return
    
    file_path = os.path.abspath(file_path)
    
    ffprobe_cmd = [
        "ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", "-show_streams", file_path
    ]
    probe_output = subprocess.check_output(ffprobe_cmd).decode('utf-8')
    probe_data = json.loads(probe_output)
    
    duration = float(probe_data['format']['duration'])
    
    segment_duration = 10
    ffmpeg_cmd = [
        "ffmpeg", "-i", file_path, "-c", "copy", "-f", "segment", 
        "-segment_time", str(segment_duration), "-reset_timestamps", "1",
        "-map", "0", "-max_muxing_queue_size", "1024", temp_output_template
    ]
    subprocess.run(ffmpeg_cmd, check=True)
    
    temp_parts = sorted([f for f in os.listdir(os.path.dirname(file_path)) if f.startswith(os.path.basename(file_path) + "_temp")])
    
    final_parts = []
    current_size = 0
    current_parts = []
    part_index = 0
    
    for temp_part in temp_parts:
        temp_part_path = os.path.join(os.path.dirname(file_path), temp_part)
        temp_part_size = os.path.getsize(temp_part_path)
        
        if current_size + temp_part_size > target_size_bytes and current_parts:
            output_file = f"{file_path}_part{part_index:03d}.mp4"
            concat_file = "concat.txt"
            with open(concat_file, "w") as f:
                for part in current_parts:
                    f.write(f"file '{part}'\n")
            
            ffmpeg_concat_cmd = [
                "ffmpeg", "-f", "concat", "-safe", "0", "-i", concat_file, "-c", "copy", output_file
            ]
            subprocess.run(ffmpeg_concat_cmd, check=True)
            
            final_parts.append(output_file)
            current_size = 0
            current_parts = []
            part_index += 1
            os.remove(concat_file)
        
        current_size += temp_part_size
        current_parts.append(temp_part_path)
    
    if current_parts:
        output_file = f"{file_path}_part{part_index:03d}.mp4"
        concat_file = "concat.txt"
        with open(concat_file, "w") as f:
            for part in current_parts:
                f.write(f"file '{part}'\n")
        
        ffmpeg_concat_cmd = [
            "ffmpeg", "-f", "concat", "-safe", "0", "-i", concat_file, "-c", "copy", output_file
        ]
        subprocess.run(ffmpeg_concat_cmd, check=True)
        
        final_parts.append(output_file)
        os.remove(concat_file)
    
    for temp_part in temp_parts:
        os.remove(os.path.join(os.path.dirname(file_path), temp_part))
    
    return final_parts

def split_video_1(file_path, target_size_mb=90):
    target_size_bytes = target_size_mb * 1024 * 1024
    temp_output_template = f"{file_path}_temp%03d.mp4"
    final_output_template = f"{file_path}_part%03d.mp4"

    if not os.access(file_path, os.R_OK):
        print(f"Không có quyền đọc file: {file_path}")
        return
    
    file_path = os.path.abspath(file_path)
    
    ffprobe_cmd = [
        "ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", "-show_streams", file_path
    ]
    probe_output = subprocess.check_output(ffprobe_cmd).decode('utf-8')
    probe_data = json.loads(probe_output)
    
    duration = float(probe_data['format']['duration'])
    
    segment_duration = 10
    ffmpeg_cmd = [
        "ffmpeg", "-i", file_path, "-c", "copy", "-f", "segment", 
        "-segment_time", str(segment_duration), "-reset_timestamps", "1",
        "-map", "0", "-max_muxing_queue_size", "1024", temp_output_template
    ]
    subprocess.run(ffmpeg_cmd, check=True)
    
    temp_parts = sorted([f for f in os.listdir(os.path.dirname(file_path)) if f.startswith(os.path.basename(file_path) + "_temp")])
    
    final_parts = []
    current_size = 0
    current_parts = []
    part_index = 0
    
    for temp_part in temp_parts:
        temp_part_path = os.path.join(os.path.dirname(file_path), temp_part)
        temp_part_size = os.path.getsize(temp_part_path)
        
        if current_size + temp_part_size > target_size_bytes and current_parts:
            output_file = f"{file_path}_part{part_index:03d}.mp4"
            concat_file = "concat.txt"
            with open(concat_file, "w") as f:
                for part in current_parts:
                    f.write(f"file '{part}'\n")
            
            ffmpeg_concat_cmd = [
                "ffmpeg", "-f", "concat", "-safe", "0", "-i", concat_file, "-c", "copy", output_file
            ]
            subprocess.run(ffmpeg_concat_cmd, check=True)
            
            final_parts.append(output_file)
            current_size = 0
            current_parts = []
            part_index += 1
            os.remove(concat_file)
        
        current_size += temp_part_size
        current_parts.append(temp_part_path)
    
    if current_parts:
        output_file = f"{file_path}_part{part_index:03d}.mp4"
        concat_file = "concat.txt"
        with open(concat_file, "w") as f:
            for part in current_parts:
                f.write(f"file '{part}'\n")
        
        ffmpeg_concat_cmd = [
            "ffmpeg", "-f", "concat", "-safe", "0", "-i", concat_file, "-c", "copy", output_file
        ]
        subprocess.run(ffmpeg_concat_cmd, check=True)
        
        final_parts.append(output_file)
        os.remove(concat_file)
    
    for temp_part in temp_parts:
        os.remove(os.path.join(os.path.dirname(file_path), temp_part))
    
    return final_parts

async def download_file(message, filename, retries=10000):
    for attempt in range(retries):
        try:
            await message.download(file_name=filename)
            return filename
        except FloodWait as e:
            print(f"Cần chờ {e.value} giây trước khi thử lại.")
            await asyncio.sleep(e.value)
        except Exception as e:
            print(f"Lỗi khi tải file: {e}. Thử lại lần thứ {attempt + 1}/{retries}")
            if attempt + 1 == retries:
                raise
            await asyncio.sleep(5)

async def ensure_telegram_login():
    try:
        await telegram_client.start()
        return True
    except Exception as e:
        print(f"Lỗi khi đăng nhập Telegram: {e}")
        return False

async def join_group_or_channel(telegram_channel):
    try:
        if telegram_channel.startswith('@'):
            telegram_channel = telegram_channel[1:]
        
        if "t.me/+" in telegram_channel or "t.me/joinchat" in telegram_channel:
            invite_link = telegram_channel
            try:
                await telegram_client.join_chat(invite_link)
                print(f"Đã tham gia vào nhóm/kênh: {telegram_channel}")
            except UserAlreadyParticipant:
                print(f"Bot đã là thành viên của nhóm/kênh: {telegram_channel}")
            except InviteHashExpired:
                print(f"Link mời đã hết hạn: {telegram_channel}")
                return None
            except InviteHashInvalid:
                print(f"Link mời không hợp lệ: {telegram_channel}")
                return None
            except FloodWaitError as e:
                print(f"Cần chờ {e.seconds} giây trước khi thử lại.")
                await asyncio.sleep(e.seconds)
                return await join_group_or_channel(telegram_channel)
        else:
            try:
                await telegram_client.join_chat(telegram_channel)
                print(f"Đã tham gia vào kênh: {telegram_channel}")
            except UserAlreadyParticipant:
                print(f"Bot đã là thành viên của kênh: {telegram_channel}")
            except UsernameInvalid:
                print(f"Tên người dùng không hợp lệ: {telegram_channel}")
                return None
            except UsernameNotOccupied:
                print(f"Tên người dùng không tồn tại: {telegram_channel}")
                return None
            except FloodWait as e:
                print(f"Cần chờ {e.value} giây trước khi thử lại.")
                await asyncio.sleep(e.value)
                return await join_group_or_channel(telegram_channel)
            except FloodWaitError as e:
                print(f"Cần chờ {e.seconds} giây trước khi thử lại.")
                await asyncio.sleep(e.seconds)
                return await join_group_or_channel(telegram_channel)
        return True
    
    except Exception as e:
        print(f"Lỗi khi tham gia vào kênh/nhóm: {e}")
        return None

async def download_and_send_messages(thread, telegram_channel, server_id):
    try:
        join_result = await join_group_or_channel(telegram_channel)
        if not join_result:
            await thread.send(f"**<a:zerotwo:1149986532678189097> Không thể tham gia vào nhóm / kênh Telegram: <{telegram_channel}>!**")
            return

        chat = await telegram_client.get_chat(telegram_channel)
        invite_id = telegram_channel.split('/')[-1]
        work_dir = f'./telegram_{invite_id}'
        os.makedirs(work_dir, exist_ok=True)

        async def process_message(message: Message):
            try:
                if message.photo:
                    file_path = await download_file(message, f"{work_dir}/{message.id}.jpg")
                    await send_file_to_discord(file_path, thread)
                elif message.video:
                    file_path = await download_file(message, f"{work_dir}/{message.id}.mp4")
                    if os.path.getsize(file_path) > 50 * 1024 * 1024:
                        if server_id == required_server_id:
                            parts = split_video_1(file_path)
                        else:
                            parts = split_video(file_path)
                        for part in parts:
                            await send_file_to_discord(part, thread)
                    else:
                        await send_file_to_discord(file_path, thread)
                elif message.document:
                    file_path = await download_file(message, f"{work_dir}/{message.document.file_name}")
                    await send_file_to_discord(file_path, thread)
            except Exception as e:
                print(f"Lỗi khi xử lý tin nhắn {message.id}: {str(e)}")

        total_messages = await telegram_client.get_chat_history_count(chat.id)
        processed = 0

        async for message in telegram_client.get_chat_history(chat.id):
            try:
                await process_message(message)
                processed += 1
                if processed % 10 == 0:
                    print(f"Logs: Đã xử lý {processed}/{total_messages} tin nhắn!")
            except FloodWait as e:
                await asyncio.sleep(e.value)

        print(f"**Logs: Đã xử lý xong {processed}/{total_messages} tin nhắn!**")

    except Exception as e:
        await thread.send(f"**<a:zerotwo:1149986532678189097> Lỗi khi tải tin nhắn: {str(e)}**")
    finally:
        if 'work_dir' in locals() and os.path.exists(work_dir):
            shutil.rmtree(work_dir)
            print(f'Đã xóa thư mục: "{work_dir}"')

async def leave_group_or_delete_messages(telegram_channel):
    try:
        chat = await telegram_client.get_chat(telegram_channel)
        if hasattr(chat, 'type'):
            if chat.type in ['supergroup', 'channel']:
                await telegram_client.leave_chat(chat.id)
                print(f"Logs: Đã rời khỏi kênh/nhóm Telegram thành công!")
                return
            elif chat.type == 'private':
                async for message in telegram_client.get_chat_history(chat.id):
                    await message.delete()
                print(f"Logs: Đã xóa tất cả tin nhắn từ người dùng / Bot thành công!")
                return
            else:
                print(f"**Logs: Không thể xác định loại chat, bỏ qua: {chat.type}!**")
                return
        else:
            print(f"**Logs: Không thể xác định loại chat này, bỏ qua!**")
            return
    except Exception as e:
        print(f"Đã xảy ra lỗi khi rời khỏi kênh/nhóm Telegram hoặc xóa tin nhắn: {str(e)}")

@bot.slash_command(description="Tải nội dung từ Telegram và gửi vào chủ đề Discord ?")
async def telegram(ctx, telegram_channel: discord.Option(str, description="Nhập Link lời mời từ Telegram vào đây!")):
    await ctx.defer()
    gif_url = "https://raw.githubusercontent.com/dragonx943/listcaidaubuoi/main/lewd.gif"
    server_id = ctx.guild.id

    try:
        guild_id = str(ctx.guild.id)
        with open('forum_channels.txt', 'r') as f:
            data = json.load(f)
        
        if guild_id not in data:
            await ctx.send_followup("**<a:zerotwo:1149986532678189097> Máy chủ này chưa đặt kênh Forum mặc định. Vui lòng sử dụng lệnh `/set-channel` trước.**")
            return
        
        forum_channel_id = data[guild_id]
        forum_channel = bot.get_channel(forum_channel_id)
        
        if not forum_channel:
            await ctx.send_followup("**<a:zerotwo:1149986532678189097> Không tìm thấy kênh Forum đã đặt trước đó. Vui lòng sử dụng lệnh `/set-channel` để đặt lại.**")
            return
        
        telegram_tag = discord.utils.get(forum_channel.available_tags, name="Telegram")
        if not telegram_tag:
            await ctx.send_followup("**<a:zerotwo:1149986532678189097> Không tìm thấy thẻ 'Telegram'. Vui lòng sử dụng lệnh `/set_channel` để tạo thẻ.**")
            return

        if telegram_channel.startswith('@https://'):
            telegram_channel = telegram_channel[1:]
        elif not (telegram_channel.startswith('https://t.me/') or telegram_channel.startswith('@')):
            await ctx.send_followup("**<a:zerotwo:1149986532678189097> Link Telegram này không hợp lệ. Hãy sử dụng Link mời hợp lệ hoặc tên người dùng bắt đầu bằng '@'.**")
            return
        
        join_result = await join_group_or_channel(telegram_channel)
        if join_result is None:
            await ctx.send_followup(f"**<a:zerotwo:1149986532678189097> Lỗi: Không thể tham gia vào nhóm/kênh: <{telegram_channel}>**")
            return
        elif join_result is True:
            print(f"Logs: Đã tham gia vào nhóm/kênh: {telegram_channel}!")
        else:
            print(f"Logs: Bot đã là thành viên của nhóm/kênh: {telegram_channel}!")

        latency = round(bot.latency * 1000)
        lmao_chat = "## Vui lòng chờ để Dora-chan tải nội dung và gửi lên Post này. Trong lúc đó, bạn có thể tham khảo các lệnh khác của Dora-chan ở dưới đây!"
        content = "# Đây là mẫu tin nhắn trả lời tự động của Dora-chan"

        embed = discord.Embed(
            title="🔗 Panel của Telegram 🌏",
            description=lmao_chat,
            color=get_random_color()
        )

        embed.add_field(name="Độ trễ / Ping", value=f"{latency} ms", inline=True)
        embed.add_field(name="Yandex -> Discord", value=f"/yandex", inline=True)
        embed.add_field(name="Lofi 24/7", value=f"/lofi", inline=True)
        embed.set_image(url=gif_url)

        thread = await forum_channel.create_thread(
            name=f"Telegram: {telegram_channel}",
            content=content,
            applied_tags=[telegram_tag],
            embed=embed
        )

        await ctx.send_followup(f"**<a:sip:1149986505964662815> Bắt đầu tải dữ liệu từ `{telegram_channel}` vào chủ đề {thread.mention}**")

        check_map = await leave_group_or_delete_messages(telegram_channel)
        print(check_map)
        await download_and_send_messages(thread, telegram_channel, server_id)
        await leave_group_or_delete_messages(telegram_channel)
        
        await thread.send(f"**<a:zerotwo:1149986532678189097> Beep~Beep~~ Dora-chan đã tải thành công dữ liệu lên bài Post này~!**")
        await ctx.channel.send(f"**<a:emoji_anime:1149986363802918922> {ctx.author.mention} Dora-chan đã làm việc xong! Xin hãy kiểm tra tại: {thread.mention}!**")
    
    except Exception as e:
        print(f"Đã xảy ra lỗi ngoài ý muốn: {e}")
        import traceback
        traceback.print_exc()
        await ctx.channel.send(f"**<a:zerotwo:1149986532678189097> Này {ctx.author.mention}, đã xảy ra lỗi ngoài ý muốn: {str(e)}**")
    
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

@bot.slash_command(description="Quản lí File máy chủ (chỉ Dev dùng)")
async def manager(ctx):
    await ctx.defer()

    if ctx.author.id != BOT_OWNER_ID:
        await ctx.followup.send("**<a:zerotwo:1149986532678189097> Đã xảy ra lỗi: Bạn không có quyền sử dụng lệnh này! Hint: Tuổi loz sánh vai?**")
        return

    embed = discord.Embed(
        title="😉 Bảng phong thần của Dev!",
        description="💻 Đây là bảng phong thần, vui lòng chọn những thiết đặt có sẵn ở dưới!",
        color=get_random_color()
    )
    embed.set_image(url="https://raw.githubusercontent.com/dragonx943/listcaidaubuoi/main/campFire.gif")

    select = Select(
        placeholder="Hãy lựa chọn tại đây...",
        options=[
            discord.SelectOption(label="➕ Thêm Cookie", value="add"),
            discord.SelectOption(label="➖ Xóa Cookie", value="delete")
        ]
    )

    async def select_callback(interaction):
        if select.values[0] == "add":
            await interaction.response.send_message("**<a:remdance:1149986502001045504> Hãy kiểm tra tin nhắn riêng tư để tải Cookie lên!**", ephemeral=True)

            dm_channel = await interaction.user.create_dm()
            await dm_channel.send("**<a:remdance:1149986502001045504> Xin hãy tải Cookie lên theo tin nhắn này!**")

            def check(m):
                return m.author == interaction.user and m.attachments

            msg = await bot.wait_for("message", check=check)
            file = msg.attachments[0]

            file_content = await file.read()
            file_content = file_content.decode("utf-8")

            if not os.path.exists('uncon_netflix'):
                os.makedirs('uncon_netflix')
            if not os.path.exists('con_netflix'):
                os.makedirs('con_netflix')

            existing_files = os.listdir('uncon_netflix')
            file_number = len(existing_files) + 1

            uncon_filename = f'netflix_cookie_{file_number}.txt'
            with open(os.path.join('uncon_netflix', uncon_filename), 'w') as txtfile:
                txtfile.write(file_content)

            cookies_json = convert_cookies_to_json_from_content(file_content)
            con_filename = f'netflix_cookie_{file_number}.json'
            with open(os.path.join('con_netflix', con_filename), 'w') as jsonfile:
                json.dump(cookies_json, jsonfile, indent=4)

            await interaction.followup.send(f"**<a:sip:1149986505964662815> Đã nhập Cookie vào Bot thành cmn công! File imported successfully!**")
            view.clear_items()

        elif select.values[0] == "delete":
            files = os.listdir('uncon_netflix')
            if not files:
                await interaction.response.send_message("**<a:zerotwo:1149986532678189097> Không có File nào để xóa hếtttttttttttt!**")
                return

            delete_options = [
                discord.SelectOption(label=filename, value=filename)
                for filename in files
            ]

            delete_select = Select(
                placeholder="Hãy chọn File để xóa...",
                options=delete_options
            )

            async def delete_select_callback(interaction):
                chosen_file = delete_select.values[0]
                json_file = chosen_file.replace('.txt', '.json')

                os.remove(os.path.join('uncon_netflix', chosen_file))
                os.remove(os.path.join('con_netflix', json_file))

                if not interaction.response.is_done():
                    await interaction.response.defer()

                await interaction.followup.send(f"**<a:sip:1149986505964662815> Đã xóa File thành công! File deleted successfully!**")

            delete_select.callback = delete_select_callback

            delete_view = View()
            delete_view.add_item(delete_select)
            await interaction.response.send_message(embed=embed, view=delete_view)

    select.callback = select_callback

    view = View()
    view.add_item(select)

    global last_add_timestamp
    last_add_timestamp = int(time.time())

    await ctx.followup.send(embed=embed, view=view)

@bot.slash_command(description="Lấy bánh quy Netflix miễn phí / Free Netflix Cookies !???")
async def send(ctx):
    await ctx.defer()

    if ctx.guild.id != required_server_id:
        await ctx.followup.send("**<a:zerotwo:1149986532678189097> Lỗi / E: Máy chủ này không được phép sử dụng lệnh này / This Discord Server is NOT ALLOWED! Hint: Chạy đâu con sâu / NO ESCAPE !???**")
        return

    role = discord.utils.get(ctx.author.roles, id=required_role_id)

    if not role:
        await ctx.followup.send("**<a:zerotwo:1149986532678189097> Lỗi / E: Chưa có quyền sử dụng lệnh này / No permission to do that! Hint: Chưa Pick Role / Role Not Found!**")
        return

    try:

        files = [f for f in os.listdir('uncon_netflix') if f.endswith('.txt')]
        if not files:
            await ctx.followup.send("**<a:zerotwo:1149986532678189097> Lỗi / E: Không có file Cookies nào trong thư mục hếtttttt / Cookies NOT FOUND!**")
            return
        chosen_file = random.choice(files)
        file_path = os.path.join('uncon_netflix', chosen_file)

        with open(file_path, 'rb') as txtfile:
            await ctx.author.send("**Hướng dẫn sử dụng bánh quy Netflix / HOW TO USE:** https://www.youtube.com/watch?v=-KDyyEmyzt0")
            await ctx.author.send(file=discord.File(txtfile, 'cookie.txt'))
            await ctx.author.send(f"**# <a:remdance:1149986502001045504> Cập nhật lần cuối / Last Update: <t:{last_add_timestamp}:R>**")

        await ctx.followup.send("**<a:sip:1149986505964662815> Đã gửi bánh quy thành công, hãy kiểm tra hộp thư đến! Cookies sent successfully, check ur inbox pls!**")
    
    except Exception as e:
        await ctx.followup.send(f"**<a:zerotwo:1149986532678189097> Đã xảy ra lỗi khi gửi bánh quy / Error:** {str(e)}")

@bot.slash_command(name="login", description="Hỗ trợ đăng nhập Netflix trên Smart TV / Automatic login Netflix for TV!")
async def login(ctx, type: discord.Option(str, description="Net của bạn là loại TV nào / What kind of TV is on screen? Ví dụ / Ex: netflix.com/tv2 -> tv2"), code: discord.Option(str, description="Nhập code của TV vào đây / Type TV Code here!")):
    await ctx.defer()

    if ctx.guild.id != required_server_id:
        await ctx.followup.send("**<a:zerotwo:1149986532678189097> Lỗi / E: Máy chủ này không được phép sử dụng lệnh này / This Discord Server is NOT ALLOWED! Hint: Chạy đâu con sâu / NO ESCAPE !???**")
        return

    role = discord.utils.get(ctx.author.roles, id=required_role_id)

    if not role:
        await ctx.followup.send("**<a:zerotwo:1149986532678189097> Lỗi / E: Chưa có quyền sử dụng lệnh này / No permission to do that! Hint: Chưa Pick Role / Role Not Found!**")
        return

    if not type.startswith("tv"):
        await ctx.followup.send("**<a:zerotwo:1149986532678189097> Loại TV bạn nhập không hợp lệ, xin hãy thử lại / Invalid TV Type, please try again! Ví dụ / Ex: netflix.com/tv2 -> Nhập / Type: tv2**")
        return

    files = [f for f in os.listdir('con_netflix') if f.endswith('.json')]
    if not files:
        await ctx.followup.send("**<a:zerotwo:1149986532678189097> Lỗi / E: Không có file Cookies nào trong thư mục hếtttttt / Cookies NOT FOUND!**")
        return

    options = [discord.SelectOption(label=f, value=f) for f in files]
    select = Select(placeholder="Hãy chọn 1 file / Choose a File!", options=options, max_values=1)

    async def select_callback(interaction):
        await interaction.response.defer()
        selected_file = select.values[0]
        driver = init_driver()
        try:
            cookie_file = os.path.join('con_netflix', selected_file)
            login_netflix(driver, type, code, cookie_file)
            await interaction.followup.send("**<a:sip:1149986505964662815> Bạn đã đăng nhập thành công vào Netflix trên TV! TV Login Successfully!**")
            await interaction.followup.send(f"**<a:remdance:1149986502001045504> Cập nhật lần cuối / Last Update: <t:{last_add_timestamp}:R>**")
        except Exception as e:
            await interaction.followup.send(f"**<a:zerotwo:1149986532678189097> Đăng nhập thất bại, xin hãy thử lại / TV Login Failed, please try again:** {str(e)}")
        finally:
            driver.quit()
        view.clear_items()
        await interaction.message.edit(view=view)
    
    select.callback = select_callback

    view = View(timeout=30)
    view.add_item(select)

    latency = round(bot.latency * 1000)

    embed = discord.Embed(
        title="🍪 Bảng đăng nhập | Login Panel 🍪",
        description="📂 Hãy chọn 1 File để đăng nhập / Please choose a File to login!",
        color=get_random_color()
    )
    embed.add_field(name="Kiểm tra cookies", value=f"/check", inline=True)
    embed.add_field(name="Check cookies", value=f"/check", inline=True)
    embed.add_field(name="Độ trễ phản hồi / Ping", value=f"{latency} ms", inline=True)
    embed.set_image(url="https://mir-s3-cdn-cf.behance.net/project_modules/hd/fb762791877129.5e3cb3903fb67.gif")

    message = await ctx.followup.send(embed=embed, view=view)

    await view.wait()
    if not select.values:
        await message.delete()

@bot.slash_command(name="steam", description="Lấy tài khoản Steam ngẫu nhiên miễn phí / Get Free Steam Accs ?")
async def steam(ctx):
    await ctx.defer()

    if ctx.guild.id != required_server_id:
        await ctx.followup.send("**<a:zerotwo:1149986532678189097> Lỗi: Không có quyền sử dụng lệnh / No Access! Hint: Chạy đâu con sâu? / Wrong Discord Server!**")
        return

    role = discord.utils.get(ctx.author.roles, id=steam_role)

    if not role:
        await ctx.followup.send("**<a:zerotwo:1149986532678189097> Lỗi: Không có quyền sử dụng / No Access! Hint: Chưa Pick Role / Steam-ers Role not found!**")
        return

    user_id = ctx.author.id
    current_time = time.time()

    if user_id in last_steam_usage and (current_time - last_steam_usage[user_id]) < 86400:
        time_remaining = 86400 - (current_time - last_steam_usage[user_id])
        future_time = current_time + time_remaining
        await ctx.followup.send(f"**<a:zerotwo:1149986532678189097> Bạn đã đạt giới hạn / Rate Limited! Thử lại sau / Try again after: <t:{int(future_time)}:R>!**")
        return

    try:
        with open('steam.txt', 'r') as file:
            lines = file.readlines()
            if lines:
                selected_line = random.choice(lines).strip()
                await ctx.author.send(f"**## <a:remdance:1149986502001045504> Tài khoản Steam của bạn là / Here is your Steam Acc:** `{selected_line}`")
                await ctx.followup.send("**<a:sip:1149986505964662815> Đã gửi tài khoản Steam thành công! Steam sent successfully!**")
                last_steam_usage[user_id] = current_time
            else:
                await ctx.followup.send("**<a:zerotwo:1149986532678189097> Lỗi: Không tìm thấy tài khoản Steam nào trong máy chủ! / Steam database not found!**")
    
    except Exception as e:
        await ctx.followup.send(f"**<a:zerotwo:1149986532678189097> Đã xảy ra lỗi khi lấy tài khoản Steam / Error:** {str(e)}")

@bot.slash_command(name="check", description="Kiểm tra Netflix hiện có / Check vaild or invaild Cookies !???")
async def check(ctx):
    await ctx.defer()

    files = os.listdir('con_netflix')
    if not files:
        await ctx.followup.send("Không có bánh nào ở đây cả / Cookies not found!")
        return
    
    timestamp = int(time.time())
    tz = pytz.timezone('Asia/Ho_Chi_Minh')
    embed_timestamp = datetime.utcfromtimestamp(timestamp).replace(tzinfo=pytz.utc).astimezone(tz)
    results = []
    for cookie_file in files:
        cookie_path = f'con_netflix/{cookie_file}'
        try:
            valid = check_cookie_validity(cookie_path)
            results.append(f"**└> {cookie_file}** {'**-> ✅**' if valid else '**-> ❌**'}")
        except Exception as e:
            results.append(f"**└> {cookie_file}** **❌ Lỗi kiểm tra / Error!**")

    embed = discord.Embed(
        title="🍪 Công cụ kiểm tra Netflix bởi Draken / Checker by Draken 🍪",
        description="**🕘 Kết quả - Result:**",
        color=get_random_color(),
        timestamp=embed_timestamp
    )
    for result in results:
        embed.add_field(name="📁 Tệp / File:", value=result, inline=True)
        embed.set_image(url="https://mir-s3-cdn-cf.behance.net/project_modules/hd/fb762791877129.5e3cb3903fb67.gif")

    await ctx.followup.send(embed=embed)

@bot.slash_command(description="Tải nội dung từ Yandex Disk và gửi vào chủ đề Discord ?")
async def yandex(ctx, yandex_link: discord.Option(str, description="Nhập link chia sẻ từ Yandex Disk vào đây!")):
    await ctx.defer()
    server_id = ctx.guild.id
    gif_url = "https://raw.githubusercontent.com/dragonx943/listcaidaubuoi/main/lewd.gif"
    temp_dir = None

    try:
        guild_id = str(ctx.guild.id)
        with open('forum_channels.txt', 'r') as f:
            data = json.load(f)
        
        if guild_id not in data:
            await ctx.send_followup("**<a:zerotwo:1149986532678189097> Máy chủ này chưa đặt kênh Forum mặc định. Vui lòng sử dụng lệnh `/set-channel` trước.**")
            return
        
        forum_channel_id = data[guild_id]
        forum_channel = bot.get_channel(forum_channel_id)
        
        if not forum_channel:
            await ctx.send_followup("**<a:zerotwo:1149986532678189097> Không tìm thấy kênh Forum đã đặt trước đó. Vui lòng sử dụng lệnh `/set-channel` để đặt lại.**")
            return
        
        yandex_tag = discord.utils.get(forum_channel.available_tags, name="Yandex")
        if not yandex_tag:
            await ctx.send_followup("**<a:zerotwo:1149986532678189097> Không tìm thấy thẻ 'Yandex'. Vui lòng sử dụng lệnh `/set_channel` để tạo thẻ.**")
            return
        
        latency = round(bot.latency * 1000)
        lmao_chat = "## Vui lòng chờ để Dora-chan tải nội dung và gửi lên Post này. Trong khi đó bạn có thể tham khảo các lệnh khác của Dora-chan ở dưới đây!"
        content = "# Đây là mẫu tin nhắn trả lời tự động của Dora-chan"
    
        embed = discord.Embed(
            title="🔗 Panel của Yandex 🌏",
            description=lmao_chat,
            color=get_random_color()
        )

        embed.add_field(name="Độ trễ / Ping", value=f"{latency} ms", inline=True)
        embed.add_field(name="Telegram -> Discord", value=f"/telegram", inline=True)
        embed.add_field(name="Lofi 24/7", value=f"/lofi", inline=True)
        embed.set_image(url=gif_url)

        thread = await forum_channel.create_thread(
            name=f"Yandex: {yandex_link}",
            content=content,
            applied_tags=[yandex_tag],
            embed=embed
        )

        await ctx.send_followup(f"**<a:sip:1149986505964662815> Bắt đầu tải dữ liệu từ `{yandex_link}` vào chủ đề {thread.mention}**")

        url = f"https://cloud-api.yandex.net/v1/disk/public/resources/download?public_key={yandex_link}"
        response = requests.get(url)
        download_url = response.json()["href"]
        
        yandex_id = urllib.parse.quote_plus(yandex_link)
        temp_dir = safe_path(os.path.abspath(f'yandex_{yandex_id}'))
        os.makedirs(temp_dir, exist_ok=True)
        print(f"Thư mục tạm thời: {temp_dir}")

        zip_path = safe_path(os.path.join(temp_dir, 'download.zip'))
        print(f"Đường dẫn file zip: {zip_path}")
        await download_file_with_retry(download_url, zip_path)

        print("Bắt đầu giải nén...")
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            safe_extract(zip_ref, temp_dir)
        print("Giải nén hoàn tất")

        os.remove(zip_path)
        print("Đã xóa file zip")

        print("**Logs: Chờ 5 giây...**")
        await asyncio.sleep(5)
        print("Đã chờ xong")

        print("Liệt kê các file trong thư mục:")
        for root, dirs, files in os.walk(temp_dir):
            for file in files:
                print(os.path.join(root, file))

        all_files = list(Path(temp_dir).rglob('*'))
        print(f"Tổng số file tìm thấy: {len(all_files)}")

        for file_path in all_files:
            if file_path.is_file():
                print(f"Đang xử lý file: {file_path}")
                if file_path.suffix.lower() in ['.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv']:
                    if file_path.stat().st_size > 50 * 1024 * 1024:
                        if server_id == required_server_id:
                            parts = split_video_1(str(file_path))
                        else:
                            parts = split_video(str(file_path))
                        for part in parts:
                            await send_file_to_discord(part, thread)
                            os.remove(part)
                    else:
                        await send_file_to_discord(str(file_path), thread)
                else:
                    await send_file_to_discord(str(file_path), thread)
            else:
                print(f"Không phải file: {file_path}")
         
        await thread.send(f"**<a:zerotwo:1149986532678189097> Beep~Beep~~ Dora-chan đã tải thành công dữ liệu lên bài Post này~!**")
        await ctx.channel.send(f"**<a:emoji_anime:1149986363802918922> {ctx.author.mention} Dora-chan đã làm việc xong! Xin hãy kiểm tra tại: {thread.mention}!**")

    except Exception as e:
        print(f"Đã xảy ra lỗi ngoài ý muốn: {e}")
        import traceback
        traceback.print_exc()
        await ctx.channel.send(f"**<a:zerotwo:1149986532678189097> Hey {ctx.author.mention}, đã có lỗi xảy ra ngoài ý muốn, hãy gọi Dev check Var ngay!**")
    finally:
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)

@bot.slash_command(description="Đặt kênh Forum mặc định cho các lệnh Telegram và Yandex")
async def set_channel(ctx, channel: discord.Option(discord.ForumChannel, description="Chọn kênh Forum mặc định để tạo Post!")):
    await ctx.defer()
    
    guild_id = str(ctx.guild.id)
    data = {}
    
    try:
        with open('forum_channels.txt', 'r') as f:
            data = json.load(f)
    except FileNotFoundError:
        pass
    
    data[guild_id] = channel.id
    
    with open('forum_channels.txt', 'w') as f:
        json.dump(data, f)
    
    existing_tags = [tag.name for tag in channel.available_tags]
    new_tags = channel.available_tags.copy()
    
    if "Telegram" not in existing_tags:
        new_tags.append(discord.ForumTag(name="Telegram", emoji="1️⃣"))
    
    if "Yandex" not in existing_tags:
        new_tags.append(discord.ForumTag(name="Yandex", emoji="2️⃣"))
    
    if len(new_tags) > len(channel.available_tags):
        try:
            await channel.edit(available_tags=new_tags)
            await ctx.send_followup(f"**<a:sip:1149986505964662815> Đã đặt kênh Forum mặc định thành {channel.mention} cho máy chủ này và cập nhật các thẻ cần thiết!**")
        except discord.Forbidden:
            await ctx.send_followup(f"**<a:sip:1149986505964662815> Đã đặt kênh Forum mặc định thành {channel.mention} cho máy chủ này, nhưng không có quyền cập nhật thẻ. Vui lòng thêm thẻ 'Telegram' và 'Yandex' thủ công.**")
        except discord.HTTPException as e:
            await ctx.send_followup(f"**<a:zerotwo:1149986532678189097> Đã xảy ra lỗi khi cập nhật thẻ: {str(e)}. Vui lòng kiểm tra lại ID emoji.**")
    else:
        await ctx.send_followup(f"**<a:sip:1149986505964662815> Đã đặt kênh Forum mặc định thành {channel.mention} cho máy chủ này. Các thẻ cần thiết đã tồn tại.**")

@bot.slash_command(description="Phát nhạc Lofi 24/7 trên 1 kênh Voice")
async def lofi(ctx, channel: discord.Option(discord.VoiceChannel, description="Chọn kênh Voice để phát nhạc 24/7!", required=False)):
    await ctx.defer()

    if channel is None:
        if ctx.author.voice:
            channel = ctx.author.voice.channel
        else:
            await ctx.send_followup("**<a:zerotwo:1149986532678189097> Bạn cần phải ở trong 1 kênh Voice hoặc chỉ định 1 kênh Voice nào đó để Bot tham gia!**")
            return

    try:
        voice_client = await channel.connect()
    except Exception as e:
        await ctx.send_followup(f"**<a:zerotwo:1149986532678189097> Lỗi: Không thể kết nối với kênh Voice: {str(e)}**")
        return

    ydl_opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'opus',
            'preferredquality': '320',
        }],
        'prefer_ffmpeg': True,
        'keepvideo': False,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info("https://www.youtube.com/watch?v=jfKfPfyJRdk", download=False)
        url = info['url']

    ffmpeg_options = {
        'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
        'options': '-vn -filter:a "volume=0.5"'
    }

    voice_client.play(discord.FFmpegPCMAudio(url, **ffmpeg_options))
    await ctx.send_followup(f"**<a:sip:1149986505964662815> Đang phát nhạc Lofi 24/7 tại {channel.mention}, hãy tận hưởng!**")
    await ctx.send_followup(f"**<a:sip:1149986505964662815> Nguồn nhạc: [lofi hip hop radio 📚 beats to relax/study to](<https://www.youtube.com/watch?v=jfKfPfyJRdk>)**")

@bot.event
async def on_ready():
    if not hasattr(bot, 'uptime'):
        bot.uptime = datetime.now()
    activity=discord.Activity(type=discord.ActivityType.playing, name="đùa với tình cảm của bạn!", state="Bạn đọc dòng này làm gì? Bạn thích tôi à?")
    await bot.change_presence(status=discord.Status.dnd, activity=activity)
    print(f'Đã đăng nhập với Bot: {bot.user}')
    await ensure_telegram_login()

if __name__ == "__main__":
    bot.run(discord_token)
