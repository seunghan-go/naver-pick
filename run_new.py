from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
import time
import requests
import os
from urllib.parse import urljoin
from random import randrange
from bs4 import BeautifulSoup
import sys
import json 
from pathlib import Path 

def find_naver_campaign_links(base_url, visited_urls_file='visited_urls.txt'):
    # Read visited URLs from file
    try:
        with open(visited_urls_file, 'r') as file:
            visited_urls = set(file.read().splitlines())
    except FileNotFoundError:
        visited_urls = set()

    # Send a request to the base URL
    response = requests.get(base_url)
    soup = BeautifulSoup(response.text, 'html.parser')

    # Find all span elements with class 'list_subject' and get 'a' tags
    list_subject_links = soup.find_all('span', class_='list_subject')
    naver_links = []
    for span in list_subject_links:
        a_tag = span.find('a', href=True)
        if a_tag and '네이버' in a_tag.text:
            naver_links.append(a_tag['href'])

    # Initialize a list to store campaign links
    campaign_links = []

    # Check each Naver link
    for link in naver_links:
        full_link = urljoin(base_url, link)
        print("naver_links - " + full_link)
        if full_link in visited_urls:
            continue  # Skip already visited links

        res = requests.get(full_link)
        inner_soup = BeautifulSoup(res.text, 'html.parser')

        # Find all links that start with the campaign URL
        for a_tag in inner_soup.find_all('a', href=True):
            if a_tag['href'].startswith("https://campaign2-api.naver.com"):
                campaign_links.append(a_tag['href'])

        # Add the visited link to the set
        visited_urls.add(full_link)

    # Save the updated visited URLs to the file
    with open(visited_urls_file, 'w') as file:
        for url in visited_urls:
            file.write(url + '\n')

    return campaign_links


def init_webdriver():
    # 크롬 드라이버 옵션 설정
    options = webdriver.ChromeOptions()
    options.add_argument('headless') # headless mode
    options.add_argument('window-size=1920x1080')
    options.add_argument('disable-gpu')    
    # 새로운 창 생성
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

    return driver

# GitHub Action을 사용하지 않을 경우, id, pw를 아래 형태로 id_pw.json 파일로 만들어 쓰시면 됩니다.
## {"USERNAME":"네이버아이디", "PASSWORD":"비번" }
def get_login_info():
    cur_file = Path(os.path.realpath(__file__))
    pw_file = cur_file.parent / 'id_pw.json'
    if pw_file.exists():
        dic = json.load(pw_file.open('r'))
        id = dic['USERNAME']
        pw = dic['PASSWORD']
        print(f"{id}, {pw}")
    else:
        id = os.getenv("USERNAME","ID is null")
        pw = os.getenv("PASSWORD","PASSWORD is null")
    return id, pw


def login_naver(driver):
    driver.get('https://naver.com')
    # 현재 열려 있는 창 가져오기
    current_window_handle = driver.current_window_handle

    # <a href class='MyView-module__link_login___HpHMW'> 일때 해당 링크 클릭
    driver.find_element(By.XPATH, "//a[@class='MyView-module__link_login___HpHMW']").click()

    # 새롭게 생성된 탭의 핸들을 찾습니다
    # 만일 새로운 탭이 없을경우 기존 탭을 사용합니다.
    new_window_handle = None
    for handle in driver.window_handles:
        if handle != current_window_handle:
            new_window_handle = handle
            break
        else:
            new_window_handle = handle

    # 새로운 탭을 driver2로 지정합니다
    driver.switch_to.window(new_window_handle)
    driver2 = driver

    username = driver2.find_element(By.NAME, 'id')
    pw = driver2.find_element(By.NAME, 'pw')

    # 로그인 정보 획득
    input_id, input_pw = get_login_info()

    # ID input 클릭
    username.click()
    # js를 사용해서 붙여넣기 발동 <- 왜 일부러 이러냐면 pypyautogui랑 pyperclip를 사용해서 복붙 기능을 했는데 운영체제때문에 안되서 이렇게 한거다.
    driver2.execute_script("arguments[0].value = arguments[1]", username, input_id)
    time.sleep(1)

    pw.click()
    driver2.execute_script("arguments[0].value = arguments[1]", pw, input_pw)
    time.sleep(1)

    #입력을 완료하면 로그인 버튼 클릭
    driver2.find_element(By.CLASS_NAME, "btn_login").click()

    time.sleep(60)  # 1분간 멈춤. 2단계 인증 쓰고 있어서 눌러줘야 함. 


def do_clipping(driver):
   
    # The base URL to start with
    base_url = "https://www.clien.net/service/board/jirum"
    #base_url = "https://www.clien.net/service/board/park"

    campaign_links = find_naver_campaign_links(base_url)
    if(campaign_links == []):
        print("모든 링크를 방문했습니다. 메인 화면 방문 - session 유지")
        campaign_links.append('https://naver.com')    
    else:
        campaign_links = list(set(campaign_links))  # 중복 제거

    for link in campaign_links:
        print(link) # for debugging
        # Send a request to the base URL
        driver.get(link)
        try:
            result = driver.switch_to.alert
            print(result.text)
            result.accept()
        except:
            print("no alert")
            pageSource = driver.page_source
            print(pageSource)
        time.sleep(1)

    time.sleep(10)


def main():
    driver = init_webdriver()

    login_naver(driver)

    if True:    ## 1회만 실행. github action의 무료 runner가 월 2000 분 limit 이 있음 발견.. 아쉽..  
        do_clipping(driver)        
    else:  # 2FA 쓰는 다른 클라우드 사용자용
        while True:
            do_clipping(driver)

            sleep_min = randrange(5, 15)
            print(f"{sleep_min}분 휴식")
            time.sleep(60*sleep_min)

if __name__ == '__main__':
    sys.exit(main())
