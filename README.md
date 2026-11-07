# download_twitter_likes
Download your liked images and videos from X / Twitter

Uses an automated browser to scroll through and download all media from your Likes tab.

Twitter appears to have blocked logging into automated browsers, so you'll have to log in through your regular browser, and then save your session cookies for this script to use. I've manually tested an extension on Chrome and Firefox that can do this without too much hassle. No guarantees on anything else working.

Chrome: J2Team Cookies - https://chromewebstore.google.com/detail/j2team-cookies/okpidcojinmlaakglciglbpcpajaibco

Firefox: Cookie-Editor - https://addons.mozilla.org/en-US/firefox/addon/cookie-editor/

## Usage:
- Install [Playwright](https://playwright.dev)
    ```
    pip install playwright
    playwright install
    ```
- Make sure you have `ffmpeg` installed and that it's accessible in your PATH.
  - You can edit the `ffmpeg_path` variable in the script to point to a specific location if needed
- Run the script
- It will prompt you to paste in a Twitter session cookie:

    ### For Chrome:
    - Log into Twitter
    - Open the extension
    - Click the down arrow next to **Export**, then click **Export as text**

    ### For Firefox:
    - Log into Twitter
    - Open the extension
    - Click the **Export** button in the bottom right
    - Click **JSON**

- Paste the contents into the prompt
- Press Enter 1-2 times
- Wait

All downloads are written to an sqlite database, to ensure no tweets are downloaded twice. So the script can be re-run without issue. It automatically exits once it hits 5 duplicate tweets.

---

This project uses some code from https://github.com/oduwsdl/tweetedat, licensed under the MIT license.
