import json
import time
import requests
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from dotenv import load_dotenv
import os

# Load environment variables from a .env file
load_dotenv()

# Path to the cookies file
cookies_file = os.getenv("COOKIES_FILE")

# URL of the webpage
content_url = os.getenv("CONTENT_URL")
website = os.getenv("WEBSITE_IMG")


def getLengthOfImages(path):
    count = 0
    # Get total number of images in the folder
    for _, _, files in os.walk(path):
        count += len(files)
    return count


start = 124
dir_path = "Gao Wu, Swallowed Star CG"
end = 146
image_prefix = os.getenv("IMAGE_PREFIX")


def load_cookies(cookies_file):
    """Load cookies from a JSON file and convert them to Selenium-compatible format."""
    try:
        with open(cookies_file, "r") as file:
            cookies = json.load(file)

            # Convert cookies to Selenium-compatible format
            converted_cookies = []
            for cookie in cookies:
                converted_cookie = {
                    "name": cookie["name"],
                    "value": cookie["value"],
                    "domain": cookie["domain"],
                    "path": cookie.get("path", "/"),
                    "secure": cookie.get("secure", False),
                }
                # Include expiry if available
                if "expirationDate" in cookie:
                    converted_cookie["expiry"] = int(cookie["expirationDate"])
                converted_cookies.append(converted_cookie)

            return converted_cookies
    except Exception as e:
        print(f"Error loading or converting cookies: {e}")
        return []


def fetch_image_url(driver, url):
    """Fetch the image URL from the given webpage."""
    try:
        # Navigate to the URL
        driver.get(url)

        # Refresh the page to apply cookies
        WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located((By.TAG_NAME, "img"))
        )

        # Get the page source after images have loaded
        page_source = driver.page_source

        # Parse with BeautifulSoup
        soup = BeautifulSoup(page_source, "html.parser")
        images = soup.find_all("img")
        return_image = (None, None)

        # Extract the first matching image URL
        for img in images:
            if "src" in img.attrs and image_prefix in img["src"]:
                return_image = (img["src"], return_image[1])
            elif "src" in img.attrs and website in img["src"]:
                return_image = (return_image[0], img["src"])

        if return_image[0] is None:
            print(f"No matching image found on {url}")

        return return_image

    except Exception as e:
        print(f"An error occurred while fetching image from {url}: {e}")
        return None


def download_image(image_url, image_name):
    """Download and save the image from the given URL."""
    try:
        response = requests.get("https:" + image_url, stream=True)
        response.raise_for_status()
        with open(image_name, "wb") as file:
            for chunk in response.iter_content(1024):
                file.write(chunk)
        print(f"Image saved: {image_name}")
    except Exception as e:
        print(f"Error downloading image {image_url}: {e}")


def get_all_images(start, end):
    """Fetch and save images from the webpage."""
    # Set up the Selenium WebDriver
    options = webdriver.ChromeOptions()
    options.headless = True
    driver = webdriver.Chrome(options=options)

    # Load cookies into the driver
    cookies_list = load_cookies(cookies_file)
    driver.get(os.getenv("BASE_URL"))  # Open the base domain to apply cookies
    for cookie in cookies_list:
        try:
            driver.add_cookie(cookie)
        except Exception as e:
            print(f"Error adding cookie {cookie}: {e}")

    # Iterate through the pages
    for i in range(start, end + 1):
        url = content_url.format(i)
        print(f"Fetching image from: {url}")
        image_dir = os.path.join(dir_path, "Images GIF")
        os.makedirs(image_dir, exist_ok=True)
        image_name = os.path.join(image_dir, f"{image_prefix} ({i - start}).gif")
        image_name2 = os.path.join(image_dir, f"{image_prefix} ({i - start})_1.gif")

        if os.path.exists(image_name):
            print(f"Image already exists: {image_name}")
            continue
        time.sleep(5)
        image_url, image_url2 = fetch_image_url(driver, url)
        if image_url is not None:
            download_image(image_url, image_name)
        if image_url2 is not None:
            download_image(image_url2, image_name2)

    # Close the driver
    driver.quit()


if __name__ == "__main__":
    get_all_images(start, end)
