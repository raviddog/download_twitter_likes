from playwright.sync_api import sync_playwright
import os
import requests
import sqlite3
import json
import random
import shutil
from datetime import datetime
from datetime import timezone

seen_urls = set()

ffmpeg_path = "D:/Files/Documents/Youtube/ffmpeg.exe"
# ffmpeg_path = "ffmpeg.exe"
ffmpeg_args = ' -protocol_whitelist "file,http,https,tcp,tls,crypto" -allowed_extensions ALL -hide_banner -loglevel error -y'

###

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

###

def save_file(url, filename, folder="images"):
    response = requests.get(url)
    filepath = os.path.join(folder, filename)
    os.makedirs(folder, exist_ok=True)
    if response.status_code == 200:
        with open(filepath, 'wb') as file:
            file.write(response.content)
    return filepath

def download_m3u8(vid_url, filename, folder="images"):
    response = requests.get(vid_url)
    filepath = os.path.join(folder, filename)
    os.makedirs(folder, exist_ok=True)
    if response.status_code == 200:
        playlist = response.text
        if "/amplify_video/" not in playlist:
            print(playlist)
            return ""
        playlist = playlist.replace("/amplify_video/", "https://video.twimg.com/amplify_video/")

        with open("playlist.m3u8", 'w') as file:
            file.write(playlist)

        ffmpeg_command = f"{ffmpeg_path} {ffmpeg_args} -i playlist.m3u8 -c copy {filepath}"
        os.system(ffmpeg_command)
        return filepath
    return ""

###

def db_check_url(url):
    cur.execute(f"SELECT * FROM downloaded WHERE url = '{url}'")
    result = cur.fetchone()
    if result:
        return True
    return False

def db_add_url(url):
    cur.execute(f"INSERT INTO downloaded (url) VALUES ('{url}')")
    con.commit()

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
        page.wait_for_timeout(3000)
        print("Loaded Likes page, now scrolling...")

        while True:
            page.mouse.wheel(0, 100000)
            delay = random.uniform(0.5, 1)
            page.wait_for_timeout(delay * 1000)

            articles = page.query_selector_all("article")

            for article in articles:
                # Check URL
                links = article.query_selector_all('a[href*="/status/"]')

                for link in links:
                    if not link:
                        continue

                    href = link.get_attribute("href")

                    # Make sure its the tweet link
                    if "photo" in href:
                        continue

                    if "analytics" in href:
                        continue

                    if "media_tags" in href:
                        continue

                    if href in seen_urls:
                        break
                    
                    if count % 25 == 0:
                        print(f"Processed {count} tweets")

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
                        if href not in seen_urls:
                            seen_urls.add(href)
                        count += 1
                        break                

                    img_count = 1
                    vid_count = 1

                    # Grab tweet embedded images
                    tweet_content = article.query_selector_all('img[src*="https://pbs.twimg.com/media/"]')
                    for tweet_media in tweet_content:
                        img_url = tweet_media.get_attribute("src")
                        img_url_source = img_url.rsplit("?")
                        if "jpg" in img_url_source[-1]:
                            img_url_download = img_url_source[0] + "?format=jpg&name=orig"
                        elif "png" in img_url_source[-1]:
                            img_url_download = img_url_source[0] + "?format=png&name=orig"
                        else:
                            # Unknown format
                            img_url_split = img_url.rsplit("/")
                            print(f"Unknown image format for file {img_url_split[-1]}")
                            continue

                        # format url
                        filename = f"{tweet_acct}-{tweet_id}-{tweet_date}-img{img_count}.jpg"
                        img_count += 1
                        # save url
                        filepath = save_file(img_url_download, filename)
                        set_file_modified_time(filepath, tweet_timestamp / 1e3)
                        
                    # Grab tweet embedded gifs
                    tweet_content = article.query_selector_all('video[src*="https://video.twimg.com/tweet_video/"]')
                    for tweet_media in tweet_content:
                        img_url_download = tweet_media.get_attribute("src")

                        # format url
                        filename = f"{tweet_acct}-{tweet_id}-{tweet_date}-img{img_count}.mp4"
                        img_count += 1
                        # save url
                        filepath = save_file(img_url_download, filename)
                        set_file_modified_time(filepath, tweet_timestamp / 1e3)

                    # Grab tweet embedded videos using resource blobs
                    tweet_content = article.query_selector_all('source[src*="blob:https://x.com/"]')
                    # Need to process these in new page, as they aren't linked by the page, instead they're downloaded resources
                    if tweet_content:
                        # Get list of video thumbnails to match to video resources in order to filter out ads on the new page
                        video_previews = article.query_selector_all('video[poster*="https://pbs.twimg.com/amplify_video_thumb/"]')
                        requested_paths = []
                        for video_preview in video_previews:
                            preview_url = video_preview.get_attribute("poster")
                            components = preview_url.rsplit('/')
                            # https://pbs.twimg.com/amplify_video_thumb/2004519052635672576/img/bxOr4K477Cb0pUqW.jpg
                            requested_paths.append(components[-3])

                        # Create new context to avoid caching the requests
                        context2 = browser.new_context(storage_state="twitter_session.json")
                        video_page = context2.new_page()
                        paths = []

                        def route_callback(route, request, paths):
                            paths.append(request.url)
                            route.continue_()

                        route_glob = "https://video.twimg.com/amplify_video/**/*.m3u8?*"
                        video_page.route(route_glob, lambda route, request: route_callback(route, request, paths))
                        video_page.goto(f"https://x.com{href}")
                        video_page.wait_for_timeout(3000)
                        video_page.unroute(route_glob)

                        for path in paths:
                            # Check that path corresponds to one of our tweet videos, and not some other content further down the page
                            for requested_path in requested_paths:
                                if requested_path in path:
                                    filename = f"{tweet_acct}-{tweet_id}-{tweet_date}-vid{vid_count}.mp4"
                                    print(path)
                                    vid_count += 1
                                    filepath = download_m3u8(path, filename)
                                    if filepath:
                                        set_file_modified_time(filepath, tweet_timestamp / 1e3)

                        video_page.close()
                        context2.close()

                    db_add_url(href)
                    seen_urls.add(href)

                    count += 1

                    print(f"Tweet #{count}: {tweet_acct} - {tweet_id} ({tweet_date}): processed {img_count-1} images, {vid_count-1} videos")
                    break
        
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

    scrape_tweets()
