from Internet.Internet_prompt import extract_question
from Internet.retrieve_Internet import retrieve_html
from client.clientfactory import Clientfactory
from env import get_app_root

import re
import os
import requests
import shutil
import threading
from typing import List
from bs4 import BeautifulSoup
from urllib3.exceptions import InsecureRequestWarning

_SAVE_PATH = os.path.join(get_app_root(), "data/cache/internet")


def InternetSearchChain(question, history):
    if os.path.exists(_SAVE_PATH):
        shutil.rmtree(_SAVE_PATH)

    if not os.path.exists(_SAVE_PATH):
        os.makedirs(_SAVE_PATH)

    whole_question = extract_question(question, history)
    question_list = re.split(r"[;；]", whole_question)

    requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

    threads = []
    links = {}

    # 为每个问题创建单独的线程
    for question in question_list:
        # 每个线程执行搜索操作
        thread = threading.Thread(target=search_bing, args=(question, links, 3))
        threads.append(thread)
        thread.start()
        thread = threading.Thread(target=search_baidu, args=(question, links, 3))
        threads.append(thread)
        thread.start()

    # 等待所有线程完成
    for thread in threads:
        thread.join()

    if has_html_files(_SAVE_PATH):
        docs, _context = retrieve_html(question)
        prompt = f"根据你现有的知识，辅助以搜索到的文件资料：\n{_context}\n 回答问题：\n{question}\n 尽可能多的覆盖到文件资料"
    else:
        prompt = question

    response = Clientfactory().get_client().chat_with_ai_stream(prompt)

    return response, links, has_html_files(_SAVE_PATH)


def search_bing(query, links, num_results=3):
    headers = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Encoding": "gzip, deflate, compress",
        "Cache-Control": "max-age=0",
        "Connection": "keep-alive",
        "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:22.0) Gecko/20100101 Firefox/22.0",
    }
    search_urls = [
        f"https://cn.bing.com/search?q={query}",
        f"https://www.bing.com/search?q={query}",
    ]
    for search_url in search_urls:
        flag = 0
        response = requests.get(search_url, headers=headers)

        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")

            for item in soup.find_all("li", class_="b_algo"):
                if flag >= num_results:
                    break
                title = item.find("h2").text
                link = item.find("a")["href"].split("#")[0]  # 删除 '#' 后的部分

                try:
                    # 禁用 SSL 验证的警告
                    response = requests.get(link, timeout=10)
                    if response.status_code == 200:
                        filename = f"{_SAVE_PATH}/{title}.html"
                        if response.text is not None:
                            with open(filename, "w", encoding="utf-8") as f:
                                links[link] = title
                                f.write(response.text)
                                flag += 1
                            print(f"Downloaded and saved: {link} as {filename}")
                        else:
                            print(f"Failed to download {link}: Empty content")
                    else:
                        print(
                            f"Failed to download {link}: Status code {response.status_code}"
                        )
                except Exception as e:
                    print(f"Error downloading {link}: {e}")
            # 检查是否达到了期望的结果数
            if flag < num_results:
                print("访问bing失败，请检查网络代理")
        else:
            print("Error: ", response.status_code)


def search_baidu(query, links, num_results=3):
    headers = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Encoding": "gzip, deflate, compress",
        "Cache-Control": "max-age=0",
        "Connection": "keep-alive",
        "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:22.0) Gecko/20100101 Firefox/22.0",
    }
    search_url = f"https://www.baidu.com/s?wd={query}"  # 百度搜索URL

    flag = 0
    response = requests.get(search_url, headers=headers)

    if response.status_code == 200:
        soup = BeautifulSoup(response.text, "html.parser")

        # 百度搜索结果的条目
        for item in soup.find_all("div", class_="result"):
            if flag >= num_results:
                break
            try:
                # 获取标题和链接
                title = item.find("h3").text
                link = item.find("a")["href"].split("#")[0]  # 删除 '#' 后的部分

                # 禁用 SSL 验证的警告
                response = requests.get(link, timeout=10)

                if response.status_code == 200:
                    filename = f"{_SAVE_PATH}/{title}.html"
                    if response.text is not None:
                        with open(filename, "w", encoding="utf-8") as f:
                            links[link] = title
                            f.write(response.text)
                            flag += 1
                        print(f"Downloaded and saved: {link} as {filename}")
                    else:
                        print(f"Failed to download {link}: Empty content")
                else:
                    print(
                        f"Failed to download {link}: Status code {response.status_code}"
                    )
            except Exception as e:
                print(f"Error downloading {link}: {e}")

        # 检查是否达到了期望的结果数
        if flag < num_results:
            print("访问百度失败，请检查网络代理制")
    else:
        print("Error: ", response.status_code)


def has_html_files(directory_path):
    if os.path.exists(directory_path):
        # 遍历目录中的文件
        for file_name in os.listdir(directory_path):
            if file_name.endswith(".html"):
                return True
        return False
    else:
        return False
