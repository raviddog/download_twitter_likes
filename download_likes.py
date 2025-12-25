from playwright.sync_api import sync_playwright
import os
import requests
import sqlite3
import json
import random
import asyncio
import shutil
import urllib.request
from datetime import datetime
from datetime import timezone

seen_urls = set()

def login():
    with sync_playwright() as p:
        browser = p.firefox.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()
        page.goto("https://x.com/login")
        input("Login. Press Enter when done")
        context.storage_state(path="twitter_session.json")
        browser.close()

def get_long_input():
    result = ""
    while True:
        user = input()
        if user == '':
            break
        result += user
    return result

def process_cookies():
    print("Paste x.com session cookies:")
    cookies = get_long_input()
    print("Processing cookies...")
    if "cookies" not in cookies:
        cookies = "{\"cookies\": " + cookies + "}"
        cookies = cookies.replace("\"sameSite\": null,", "\"sameSite\": \"None\"," )

    cookies = cookies.replace("no_restriction", "None")
    cookies = cookies.replace("unspecified", "None")
    cookies = cookies.replace("lax", "Lax")

    with open("twitter_session.json", "w") as f:
        f.write(cookies)

    print("Cookies saved")


def save_file(url, filename, folder="images"):
    os.makedirs(folder, exist_ok=True)
    filepath = os.path.join(folder, filename)
    urllib.request.urlretrieve(url, filepath)
    return filepath

def db_check_url(url):
    cur.execute(f"SELECT * FROM downloaded WHERE url = '{url}'")
    result = cur.fetchone()
    if result:
        return True
    return False

def db_add_url(url):
    cur.execute(f"INSERT INTO downloaded (url) VALUES ('{url}')")
    con.commit()

def db_load_all_urls():
    cur.execute("SELECT url FROM downloaded")
    query = cur.fetchall()
    for url in query:
        seen_urls.add(url[0])

def set_file_modified_time(filename, time):
    ctime = os.path.getctime(filename)
    os.utime(filename, (ctime, time))

# https://github.com/oduwsdl/tweetedat
def find_tweet_timestamp_post_snowflake(tid):
    offset = 1288834974657
    tstamp = (int(tid) >> 22) + offset
    return tstamp

def scrape_tweets():
    print("Connecting to Twitter...")
    url = "https://x.com/"
    count = 0

    with sync_playwright() as p:
        browser = p.firefox.launch(headless=True)
        context = browser.new_context(storage_state="twitter_session.json")
        page = context.new_page()
        page.goto(url)
        page.wait_for_timeout(5000)

        # Browse to profile likes page
        profile = page.query_selector('a[aria-label="Profile"]')
        if not profile:
            input("⛔ Error: couldn't find profile. Maybe your session cookies don't contain an active login.")
            return
        account = profile.get_attribute("href")
        if not account:
            input("⛔ Error: couldn't find profile. Maybe your session cookies don't contain an active login.")
            return
        account = account.strip('/')

        page.goto(f"https://x.com/{account}/likes")
        page.wait_for_timeout(5000)
        print("Loaded Likes page, now downloading...")

        while True:
            page.mouse.wheel(0, 2000)
            delay = random.uniform(2.5, 3)
            page.wait_for_timeout(delay * 1000)

            articles = page.query_selector_all("article")

            for article in articles:
                # Check URL
                link = article.query_selector('a[href*="/status/"]')
                if not link:
                    continue

                href = link.get_attribute("href")

                # Make sure its the tweet link
                if "photo" in href:
                    continue

                if "analytics" in href:
                    continue

                if href in seen_urls:
                    count += 1
                    continue

                # Grab tweet details
                # account, post id, date, img count
                tweet_url = href.rsplit("/")
                tweet_id = tweet_url[-1]
                tweet_acct = tweet_url[-3]
                tweet_timestamp = find_tweet_timestamp_post_snowflake(tweet_id)
                tweet_datetime = datetime.fromtimestamp(tweet_timestamp / 1e3, tz=timezone.utc)
                tweet_date = tweet_datetime.strftime("%Y%m%d_%H%M%S")
                
                # Check for duplicate
                if db_check_url(href):
                    print(f"Already downloaded: {tweet_acct} - {tweet_id} ({tweet_date}) {href}")
                    count += 1
                    continue                

                img_count = 1
                vid_count = 1

                # Grab tweet embedded images
                tweet_images = article.query_selector_all('img[src*="https://pbs.twimg.com/media/"]')
                for tweet_image in tweet_images:
                    img_url = tweet_image.get_attribute("src")
                    img_url_split = img_url.rsplit("?")
                    img_url_download = img_url_split[0] + "?format=jpg&name=large"

                    # format url
                    filename = f"{tweet_acct}-{tweet_id}-{tweet_date}-img{img_count}.jpg"
                    img_count += 1
                    # save url
                    filepath = save_file(img_url_download, filename)
                    set_file_modified_time(filepath, tweet_timestamp / 1e3)
                    
                # Grab tweet embedded videos
                tweet_images = article.query_selector_all('video[src*="https://video.twimg.com/tweet_video/"]')
                for tweet_image in tweet_images:
                    img_url_download = tweet_image.get_attribute("src")

                    # format url
                    filename = f"{tweet_acct}-{tweet_id}-{tweet_date}-vid{vid_count}.mp4"
                    vid_count += 1
                    # save url
                    filepath = save_file(img_url_download, filename)
                    set_file_modified_time(filepath, tweet_timestamp / 1e3)

                db_add_url(href)
                seen_urls.add(href)

                count += 1

                print(f"Tweet #{count}: {tweet_acct} - {tweet_id} ({tweet_date}): processed {img_count-1} images, {vid_count-1} videos")
        
        browser.close()


if __name__ == "__main__":
    if not os.path.isfile("twitter_session.json"):
        process_cookies()
        # print("❌ Login is currently blocked by X, and no existing cookies found.\nPlease save existing session cookies from your browser into a file \"twitter_session.json\" and try again.")
        # quit()
        # login()

    if not os.path.isfile("downloaded.db"):
        shutil.copyfile("downloaded_clean.db", "downloaded.db")

    con = sqlite3.connect("downloaded.db")
    cur = con.cursor()

    db_load_all_urls()

    scrape_tweets()
