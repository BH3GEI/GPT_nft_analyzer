import os
import csv
import base64
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from openai import OpenAI
import requests
from urllib.parse import urlparse
from pathlib import Path

INPUT_CSV = "links.csv"
OUTPUT_FOLDER = "foundation_images"
OUTPUT_CSV = "analysis_results.csv"
IMAGE_SELECTOR = "#__next > div:nth-child(4) > div > div.st--c-dHNLqK > div > div > div > div > img"
FAILED_URLS_CSV = "failed_urls.csv"

# 这里可以设置环境变量配置apikey，官网推荐这样做，但是这里我直接指定为我自己的apikey了
XAI_API_KEY = os.getenv("XAI_API_KEY")
client = OpenAI(
    api_key="xai-jB7x8OhQkpKShnc7PfXIy2lVCtnbAeCnJJyURgSuzwaxLc8jxAw4ITpoxwMGpbigog6EH1KgYLzvFfI1",
    base_url="https://api.x.ai/v1",
)

def setup_driver():
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    return webdriver.Chrome(options=options)

def get_image_url(driver, url):
    driver.get(url)
    try:
        img_element = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, IMAGE_SELECTOR))
        )
        return img_element.get_attribute('src')
    except Exception as e:
        print(f"Error getting image from {url}: {e}")
        return None

def download_image(image_url, output_path):
    try:
        response = requests.get(image_url)
        response.raise_for_status()
        with open(output_path, 'wb') as f:
            f.write(response.content)
        return True
    except Exception as e:
        print(f"Error downloading image {image_url}: {e}")
        return False

def analyze_image(image_path):
    with open(image_path, "rb") as image_file:
        base64_image = base64.b64encode(image_file.read()).decode("utf-8")

    messages = [
        {
            "role": "user",
            "content": [
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{base64_image}",
                        "detail": "high",
                    },
                },
                {
                    "type": "text",
                    "text": "Describe this NFT artwork in detail.",
                },
            ],
        },
    ]

    try:
        response = client.chat.completions.create(
            model="grok-vision-beta",
            messages=messages,
            stream=False,
            temperature=0.01,
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"Error analyzing image: {e}")
        return None

def get_processed_urls():
    processed_urls = set()
    
    if os.path.exists(OUTPUT_CSV):
        with open(OUTPUT_CSV, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            next(reader)  
            processed_urls.update(row[0] for row in reader)
    
    if os.path.exists(FAILED_URLS_CSV):
        with open(FAILED_URLS_CSV, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            next(reader)  
            processed_urls.update(row[0] for row in reader)
    
    return processed_urls

def main():
    os.makedirs(OUTPUT_FOLDER, exist_ok=True)

    processed_urls = get_processed_urls()
    
    driver = setup_driver()
    
    if not os.path.exists(OUTPUT_CSV):
        with open(OUTPUT_CSV, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['URL', 'Analysis'])
    
    if not os.path.exists(FAILED_URLS_CSV):
        with open(FAILED_URLS_CSV, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['URL', 'Error'])
    
    with open(INPUT_CSV, 'r') as f:
        urls = [line.strip() for line in f if line.strip()]
    
    for url in urls:
        if url in processed_urls:
            print(f"跳过已处理的URL: {url}")
            continue
            
        print(f"Processing {url}")
        try:
            image_url = get_image_url(driver, url)
            if not image_url:
                raise Exception("Failed to get image URL")
                
            filename = f"{urlparse(url).path.replace('/', '_')}.png"
            image_path = os.path.join(OUTPUT_FOLDER, filename)
            
            if not download_image(image_url, image_path):
                raise Exception("Failed to download image")
            
            analysis = analyze_image(image_path)
            if not analysis:
                raise Exception("Failed to analyze image")
            
            with open(OUTPUT_CSV, 'a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([url, analysis])
                
            print(f"Successfully processed and saved result for {url}")
            
        except Exception as e:
            print(f"Failed to process {url}: {e}")
            with open(FAILED_URLS_CSV, 'a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([url, str(e)])
                
        time.sleep(2)
    
    driver.quit()

if __name__ == "__main__":
    main()
