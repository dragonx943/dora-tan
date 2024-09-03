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
from discord.ui import Select, View
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
import requests
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
telegram_client = TelegramClient('', api_id, api_hash)

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

def get_random_color():
    return discord.Color(random.randint(0, 0xFFFFFF))

def download_file_with_retry(url, local_filename):
    session = requests.Session()
    retry = Retry(total=5, backoff_factor=0.1, status_forcelist=[500, 502, 503, 504])
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)

    with session.get(url, stream=True) as r:
        r.raise_for_status()
        with open(local_filename, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192): 
                if chunk:
                    f.write(chunk)
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

def split_video_1(file_path, target_size_mb=90):
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

async def download_file(media, filename, retries=100):
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

async def download_and_send_messages(thread, telegram_channel, server_id):
    entity = await join_group_or_channel(telegram_channel)
    if entity == 'already_a_participant':
        await thread.send("**<a:zerotwo:1149986532678189097> Lỗi: Nhóm / Kênh đã được tham gia trước đó, vui lòng dùng `/leave_telegram` để rời nhóm / kênh**")
        return
    if not entity:
        await thread.send("**<a:zerotwo:1149986532678189097> Đã xảy ra lỗi khi tham gia vào nhóm / kênh Telegram. Xin hãy cung cấp 1 Link lời mời hợp lệ!**")
        return

    invite_id = telegram_channel.split('/')[-1]
    work_dir = f'./telegram_{invite_id}'
    os.makedirs(work_dir, exist_ok=True)

    async def process_message(index, message, total_messages):
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
                if server_id == required_server_id:
                    parts = split_video_1(filename)
                else:
                    parts = split_video(filename)
                for part in parts:
                    await send_file_to_discord(part, thread)
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
        tasks = [process_message(index, message, total_messages) for index, message in enumerate(messages, start=1)]
        await asyncio.gather(*tasks)

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
async def telegram(ctx, discord_thread_id: discord.Option(str, description="Nhập ID chủ đề Discord vào đây!"), telegram_channel: discord.Option(str, description="Nhập Link mời từ Telegram vào đây!")):
    await ctx.defer()
    server_id = ctx.guild.id

    try:
        await ctx.send_followup(f"**<a:sip:1149986505964662815> Bắt đầu tải dữ liệu từ `{telegram_channel}` vào chủ đề <#{discord_thread_id}>**")
        thread = bot.get_channel(int(discord_thread_id))
        if thread is None:
            await ctx.send_followup(f'**<a:zerotwo:1149986532678189097> Không thể tìm thấy chủ đề với ID: `{discord_thread_id}` trên Discord!**')
            return
        if thread.last_message and thread.last_message.content == "**<a:zerotwo:1149986532678189097> Lỗi: Nhóm / Kênh đã được tham gia trước đó, vui lòng dùng `/leave_telegram` để rời nhóm / kênh**":
            await ctx.send_followup(f"**<a:zerotwo:1149986532678189097> Đã xảy ra lỗi ngoài ý muốn! Vui lòng kiểm tra lỗi tại: <#{discord_thread_id}>!**")
        else:
            await download_and_send_messages(thread, telegram_channel, server_id)
            await ctx.send_followup(f"**<a:emoji_anime:1149986363802918922> Đã thực thi xong câu lệnh! Xin hãy kiểm tra tại: <#{discord_thread_id}>!**")
    except Exception as e:
        print(f"Đã xảy ra lỗi ngoài ý muốn: {e}")
        await ctx.send_followup(f"**<a:zerotwo:1149986532678189097> Đã xảy ra lỗi ngoài ý muốn, vui lòng kiểm tra tại máy chủ!**")

@bot.slash_command(description="Rời khỏi kênh / nhóm Telegram hoặc xóa tất cả tin nhắn từ người dùng / Bot Telegram ?")
async def leave_telegram(ctx, telegram_channel: discord.Option(str, description="Nhập Link từ Telegram vào đây!")):
    await ctx.defer()
    try:
        result = await leave_group_or_delete_messages(telegram_channel)
        await ctx.send_followup(f"**<a:zerotwo:1149986532678189097> {result}**")
    except Exception as e:
        await ctx.send_followup(f"**<a:zerotwo:1149986532678189097> Đã xảy ra lỗi ngoài ý muốn!**")

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
            await dm_channel.send("**<a:remdance:1149986502001045504> Xin hãy tải Cookie lên theo tin nhắn này: **")

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

                # Delete the files
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
    embed.add_field(name="Độ trễ phản hồi", value=f"{latency} ms", inline=True)
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

    if user_id in last_steam_usage and (current_time - last_steam_usage[user_id]) < 172800:
        time_remaining = 172800 - (current_time - last_steam_usage[user_id])
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
async def yandex(ctx, discord_thread_id: discord.Option(str, description="Nhập ID chủ đề Discord vào đây!"), yandex_link: discord.Option(str, description="Nhập link chia sẻ từ Yandex Disk vào đây!")):
    await ctx.defer()
    server_id = ctx.guild.id

    try:
        await ctx.send_followup(f"**<a:sip:1149986505964662815> Bắt đầu tải dữ liệu từ `{yandex_link}` vào chủ đề <#{discord_thread_id}>**")
        thread = bot.get_channel(int(discord_thread_id))
        if thread is None:
            await ctx.send_followup(f'**<a:zerotwo:1149986532678189097> Không thể tìm thấy chủ đề với ID: `{discord_thread_id}` trên Discord!**')
            return

        yandex_id = urllib.parse.quote_plus(yandex_link)
        temp_dir = f'./yandex_{yandex_id}'
        os.makedirs(temp_dir, exist_ok=True)

        url = f"https://cloud-api.yandex.net/v1/disk/public/resources/download?public_key={yandex_link}"
        response = requests.get(url)
        download_url = response.json()["href"]
        
        zip_path = os.path.join(temp_dir, 'download.zip')
        download_file_with_retry(download_url, zip_path)

        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(temp_dir)

        for root, dirs, files in os.walk(temp_dir):
            for file in files:
                if file == 'download.zip':
                    continue
                file_path = os.path.join(root, file)
                if file.lower().endswith(('.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv')):
                    if os.path.getsize(file_path) > 50 * 1024 * 1024:
                        if server_id == required_server_id:
                            parts = split_video_1(file_path)
                        else:
                            parts = split_video(file_path)
                        for part in parts:
                            await send_file_to_discord(part, thread)
                            os.remove(part)
                    else:
                        await send_file_to_discord(file_path, thread)
                else:
                    await send_file_to_discord(file_path, thread)

        await ctx.send_followup(f"**<a:emoji_anime:1149986363802918922> Đã thực thi xong câu lệnh! Xin hãy kiểm tra tại: <#{discord_thread_id}>!**")

    except Exception as e:
        print(f"Đã xảy ra lỗi ngoài ý muốn: {e}")
        await ctx.send_followup(f"**<a:zerotwo:1149986532678189097> Đã xảy ra lỗi ngoài ý muốn, vui lòng kiểm tra tại máy chủ!**")
    finally:
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)

@bot.event
async def on_ready():
    if not hasattr(bot, 'uptime'):
        bot.uptime = datetime.now()
    activity=discord.Activity(type=discord.ActivityType.playing, name="đùa với tình cảm của bạn!", state="Bạn đọc dòng này làm gì? Bạn thích tôi à?")
    await bot.change_presence(status=discord.Status.dnd, activity=activity)
    print(f'Đã đăng nhập với Bot: {bot.user}')

bot.run(discord_token)
