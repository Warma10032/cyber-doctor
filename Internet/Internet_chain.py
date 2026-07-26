from Internet.Internet_prompt import extract_question
from Internet.retrieve_Internet import retrieve_html
from Internet.youcom_search import search_news as youcom_search
from client.clientfactory import Clientfactory
from env import get_app_root

import re
import os
import requests
import shutil
import threading
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

    # Try You.com Search first, fall back to Bing/Baidu scraping
    youcom_result = try_youcom_search(whole_question)
    if youcom_result is not None:
        links = youcom_result.get("links", {})
        if youcom_result.get("has_files"):
            docs, _context = retrieve_html(question)
            prompt = f"根据你现有的知识，辅助以搜索到的文件资料：\n{_context}\n 回答问题：\n{question}\n 尽可能多的覆盖到文件资料"
        else:
            prompt = youcom_result.get("response", question)
        response = Clientfactory().get_client().chat_with_ai_stream(prompt)
        return response, links, youcom_result.get("has_files", False)

    # Fall back to Bing/Baidu scraping
    links = {}
    threads = []
    for q in question_list:
        thread = threading.Thread(target=search_bing, args=(q, links, 3))
        threads.append(thread)
        thread.start()
        thread = threading.Thread(target=search_baidu, args=(q, links, 3))
        threads.append(thread)
        thread.start()

    for thread in threads:
        thread.join()

    if has_html_files(_SAVE_PATH):
        docs, _context = retrieve_html(question)
        prompt = f"根据你现有的知识，辅助以搜索到的文件资料：\n{_context}\n 回答问题：\n{question}\n 尽可能多的覆盖到文件资料"
    else:
        prompt = question

    response = Clientfactory().get_client().chat_with_ai_stream(prompt)

    return response, links, has_html_files(_SAVE_PATH)


def try_youcom_search(question: str) -> dict | None:
    """Try You.com Search. Returns dict with response/links/has_files or None if unavailable."""
    from env import get_env_value
    if not get_env_value("YOUCOM_API_KEY"):
        return None

    try:
        result = youcom_search(question, count=10)
    except Exception:
        return None

    if result.startswith("You.com") or result.startswith("No results"):
        return None

    # Write synthetic HTML files so retrieve_html下游 can process them
    links = {}
    if result and not result.startswith("No results"):
        lines = result.split("\n\n")
        for i, line in enumerate(lines):
            if line.startswith("["):
                parts = line.split("\n")
                if len(parts) >= 2:
                    title = parts[0]
                    url_line = next((p for p in parts if p.startswith("   URL:")), None)
                    if url_line:
                        url = url_line.replace("   URL:", "").strip()
                        filename = f"{_SAVE_PATH}/youcom_result_{i}.html"
                        content = f"<html><body><h1>{title}</h1><p>{line}</p></body></html>"
                        with open(filename, "w", encoding="utf-8") as f:
                            f.write(content)
                        links[url] = title

    return {
        "response": result,
        "links": links,
        "has_files": bool(links),
    }


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
        # 禁用 SSL 验证的警告
        response = requests.get(search_url, headers=headers, verify=False)

        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")

            for item in soup.find_all("li", class_="b_algo"):
                if flag >= num_results:
                    break
                title = item.find("h2").text
                link = item.find("a")["href"].split("#")[0]  # 删除 '#' 后的部分

                try:
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
    # 禁用 SSL 验证的警告
    response = requests.get(search_url, headers=headers, verify=False)

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
            print("访问百度失败，请检查网络代理")
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
