import random
import os
import urllib.parse
import discord
from discord.ext import commands
import requests
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import NoSuchElementException
from bs4 import BeautifulSoup

is_command_executing = False

intents = discord.Intents.all()

headers = {
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
    'User-Agent': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9'
}

bot = commands.Bot(command_prefix='!', intents=intents)

def last_page():
    url = 'https://itorrents-igruha.org/newgames/page/1/'
    response = requests.get(url=url, headers=headers)
    content = response.content
    soup = BeautifulSoup(content, 'html.parser')
    page_num = soup.find('div', id='pages')
    last_page = page_num.find_all('a')[-1]['href']
    last_digit = int(last_page.split('/')[-2])
    return last_digit

def url_collect():
    random_page = random.randint(1, last_page())
    url1 = f'https://itorrents-igruha.org/newgames/page/{random_page}/'
    response = requests.get(url=url1, headers=headers)
    content = response.content
    soup = BeautifulSoup(content, 'html.parser')
    game_titles = soup.find_all('div', class_='article-film-title')
    random_game_element = random.choice(game_titles)
    game_title = random_game_element.text.strip()
    game_link = random_game_element.find('a')['href']
    game_response = requests.get(url=game_link, headers=headers)
    game_content = game_response.content
    game_soup = BeautifulSoup(game_content, 'html.parser')
    torrent_link = game_soup.find('a', class_='torrent')['href']
    print(game_title, ':', game_link, ':', torrent_link)

    poster_div = game_soup.find('div', id='article-film-full-poster-bg')
    img_src = poster_div.find('img')['src']
    image_response = requests.get(url=img_src, headers=headers)
    image_file_name = f"{game_title}.jpg"
    with open(image_file_name, "wb") as file:
        file.write(image_response.content)
    print(f"Картинка скачана: {image_file_name}")

    torrent_response = requests.get(url=torrent_link, headers=headers)
    file_link = ''
    torrent_soup = BeautifulSoup(torrent_response.content, 'html.parser')
    if torrent_soup.find('a', class_='torrent2'):
        file_link = torrent_soup.find('a', class_='torrent2')['href']
    else:
        print("Торрент-файл не найден")

    if file_link:
        file_response = requests.get(url=file_link, headers=headers)
        torrent_file_name = f"{game_title}.torrent"
        with open(torrent_file_name, "wb") as file:
            file.write(file_response.content)
        print(f"Файл скачан: {torrent_file_name}")
    else:
        return game_title, game_link, None, image_file_name

    return game_title, game_link, torrent_file_name, image_file_name


@bot.command()
async def rg(ctx):


    game_title, game_link, filename, image_filename = url_collect()


    # await ctx.send(embed=embed)

    if filename:
        with open(filename, 'rb') as file:
            embed = discord.Embed(title=game_title, url=game_link)

            with open(image_filename, 'rb') as image_file:
                files = [discord.File(file), discord.File(image_file)]
                await ctx.send(embed=embed, files=files)

        os.remove(filename)
        os.remove(image_filename)
    else:
        embed = discord.Embed(title=game_title, url=game_link)
        await ctx.send(embed=embed)
        await ctx.send("Торрент-файл не найден")

@bot.command()
async def gf(ctx, query):
    global is_command_executing

    if is_command_executing:
        await ctx.send("Команда уже выполняется. Пожалуйста, дождитесь ее завершения.")
        return

    try:
        is_command_executing = True  # Устанавливаем состояние выполнения команды в True

        await ctx.send("Начинаю поиск...")
        driver_path = r'ПУТЬ К ДРАЙВЕРУ'
        os.environ["PATH"] += os.pathsep + driver_path

        # Создание объекта опций Chrome
        chrome_options = Options()

        # Установка опции для скрытия окна браузера
        chrome_options.add_argument("--headless")

        # Инициализация драйвера браузера с опциями
        driver = webdriver.Chrome(options=chrome_options)

        driver.get("https://itorrents-igruha.org/newgames/page/1/")
        search_input = driver.find_element("id", "story")
        search_input.clear()
        search_input.send_keys(query)
        search_input.send_keys(Keys.ENTER)
        driver.implicitly_wait(5)

        try:
            # Нахождение первой карточки с помощью CSS-селектора
            card_title = driver.find_element("css selector", ".article-film-title > a")
            title = card_title.text
            # Получение ссылки первой карточки
            card_link = card_title.get_attribute("href")

            # Переход по ссылке первой карточки
            driver.get(card_link)
            page_source = driver.page_source

            # Нахождение ссылки для скачивания торрента
            torrent_link = driver.find_element("css selector", "a.torrent").get_attribute("href")

            # Переход по ссылке для скачивания торрента
            driver.get(torrent_link)

            # Нахождение ссылки для скачивания файла
            file_link = driver.find_element("css selector", "a.torrent2").get_attribute("href")

            # Получение имени файла из ссылки
            file_name = urllib.parse.unquote(os.path.basename(urllib.parse.urlparse(file_link).query))

            # Загрузка файла с помощью requests
            response = requests.get(file_link)
            file_path = os.path.join(os.getcwd(), file_name)
            with open(file_path, 'wb') as file:
                file.write(response.content)

            invalid_chars = r'\/:*?"<>|'
            for char in invalid_chars:
                title = title.replace(char, '')

            new_file_name = f"{title}.torrent" + os.path.splitext(file_name)[1]  # Новое имя файла
            new_file_path = os.path.join(os.getcwd(), new_file_name)
            os.rename(file_path, new_file_path)

            # Создание объекта BeautifulSoup для парсинга страницы
            soup = BeautifulSoup(page_source, 'html.parser')

            # Нахождение элемента <img> с классом "entry-image"
            image_element = soup.find('img', class_='article-img-full entry-image')

            if image_element:
                # Получение ссылки на изображение
                image_url = image_element['src']

                # Скачивание изображения с помощью Requests
                image_response = requests.get(image_url)
                image_name = "cover.jpg"  # Имя файла изображения
                image_path = os.path.join(os.getcwd(), image_name)
                with open(image_path, 'wb') as image_file:
                    image_file.write(image_response.content)

                # Отправка сообщения в Discord скачанными данными
                embed = discord.Embed(title=title)
                embed.set_image(url=f"attachment://{image_name}")

                # Отправка изображения и торрент-файла в Discord
                with open(new_file_path, 'rb') as file, open(image_path, 'rb') as image_file:
                    await ctx.send(file=discord.File(file, filename=new_file_name))
                    await ctx.send(file=discord.File(image_file, filename=image_name), embed=embed)

                await ctx.send(f"Игра: {title} \nСсылка: {card_link}")
            else:
                await ctx.send("Игра не найдена")

            os.remove(new_file_path)
            os.remove(image_path)
        except NoSuchElementException:
            await ctx.send("Игра не найдена")

        driver.quit()
    except Exception as e:
        await ctx.send(f"Произошла ошибка при выполнении команды: {str(e)}")

    finally:
        is_command_executing = False  # Устанавливаем состояние выполнения команды в False после выполнения или ошибки

@bot.command()
async def stop(ctx):
    global is_command_executing

    if is_command_executing:
        is_command_executing = False
        await ctx.send("Выполнение команды отменено.")
    else:
        await ctx.send("Нет активной команды для отмены.")

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return  # Ignore the error silently

    # Handle other types of errors if needed
    print(f"Error occurred: {error}")

bot.run('БОТ-ТОКЕН')

