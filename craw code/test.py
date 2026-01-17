import requests
from bs4 import BeautifulSoup
import json
import time
import re
import csv
from urllib.parse import urljoin

def crawl_nhc_policies_with_content():
    # 第一级：爬取政策列表
    list_url = "https://www.nhc.gov.cn/wjw/gfxwjj/list.shtml"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    }
    
    policy_data = []
    
    try:
        # 爬取列表页
        response = requests.get(list_url, headers=headers, timeout=10)
        response.raise_for_status()
        response.encoding = 'utf-8'
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 提取政策链接 - 根据实际网页结构调整选择器
        policy_links = []
        
        # 方法1：尝试查找所有包含政策链接的a标签
        for a_tag in soup.find_all('a', href=True):
            href = a_tag['href']
            # 筛选可能是政策详情页的链接
            if ('.shtml' in href and 
                any(keyword in a_tag.get_text() for keyword in ['通知', '公告', '指南', '办法', '规定', '意见', '方案'])):
                
                # 补全链接
                full_url = urljoin(list_url, href)
                title = a_tag.get_text().strip()
                
                if title and len(title) > 5:  # 过滤有效标题
                    policy_links.append({
                        'title': title,
                        'url': full_url
                    })
        
        print(f"找到 {len(policy_links)} 个政策链接")
        
        # 第二级：逐个爬取政策详情内容
        for i, policy in enumerate(policy_links[:20]):  # 先测试前20个，成功后改为len(policy_links)
            try:
                print(f"正在爬取第 {i+1}/{len(policy_links)} 个政策: {policy['title']}")
                
                # 爬取详情页
                detail_response = requests.get(policy['url'], headers=headers, timeout=15)
                detail_response.encoding = 'utf-8'
                
                if detail_response.status_code == 200:
                    detail_soup = BeautifulSoup(detail_response.text, 'html.parser')
                    
                    # 提取政策内容 - 这里需要根据实际页面结构调整
                    content = extract_policy_content(detail_soup)
                    
                    # 提取发布日期和来源
                    pub_date = extract_publication_date(detail_soup)
                    source = extract_source(detail_soup)
                    
                    policy_info = {
                        'title': policy['title'],
                        'url': policy['url'],
                        'publication_date': pub_date,
                        'source': source,
                        'content': content,
                        'content_length': len(content),
                        'crawl_time': time.strftime('%Y-%m-%d %H:%M:%S')
                    }
                    
                    policy_data.append(policy_info)
                    print(f"✓ 成功爬取内容，长度: {len(content)} 字符")
                    
                else:
                    print(f"✗ 无法访问页面: {detail_response.status_code}")
                
                # 礼貌延迟，避免请求过快
                time.sleep(2)
                
            except Exception as e:
                print(f"✗ 爬取单个政策失败: {e}")
                continue
        
        # 保存完整数据
        if policy_data:
            # 保存为JSON
            with open('policies_with_content.json', 'w', encoding='utf-8') as f:
                json.dump(policy_data, f, ensure_ascii=False, indent=2)
            
            # 保存为CSV（不含内容，因为内容太长）
            with open('policies_summary.csv', 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f)
                writer.writerow(['标题', '链接', '发布日期', '来源', '内容长度', '爬取时间'])
                for policy in policy_data:
                    writer.writerow([
                        policy['title'], 
                        policy['url'], 
                        policy['publication_date'],
                        policy['source'],
                        policy['content_length'],
                        policy['crawl_time']
                    ])
            
            # 单独保存内容文本文件
            with open('policy_contents.txt', 'w', encoding='utf-8') as f:
                for policy in policy_data:
                    f.write(f"【标题】{policy['title']}\n")
                    f.write(f"【链接】{policy['url']}\n")
                    f.write(f"【日期】{policy['publication_date']}\n")
                    f.write(f"【来源】{policy['source']}\n")
                    f.write(f"【内容】\n{policy['content']}\n")
                    f.write("="*80 + "\n\n")
            
            print(f"🎉 成功爬取并保存了 {len(policy_data)} 条政策的完整内容！")
            print(f"📊 数据文件: policies_with_content.json, policies_summary.csv, policy_contents.txt")
            
        else:
            print("未找到任何政策内容")
            
    except Exception as e:
        print(f"爬取过程中出错: {e}")

def extract_policy_content(soup):
    """提取政策正文内容"""
    # 尝试多种可能的内容区域选择器
    content_selectors = [
        'div.content',
        'div.TRS_Editor',
        'div.article-content',
        'div.text',
        'div#content',
        'div.main-content'
    ]
    
    for selector in content_selectors:
        content_div = soup.select_one(selector)
        if content_div:
            # 清理无关元素
            for elem in content_div(['script', 'style', 'nav', 'header', 'footer']):
                elem.decompose()
            
            text = content_div.get_text(separator='\n', strip=True)
            if len(text) > 100:  # 确保有足够内容
                return text
    
    # 如果特定选择器失败，尝试获取整个正文的文本
    body = soup.find('body')
    if body:
        # 移除导航、页眉页脚等
        for elem in body(['script', 'style', 'nav', 'header', 'footer', 'aside']):
            elem.decompose()
        
        return body.get_text(separator='\n', strip=True)
    
    return "无法提取内容"

def extract_publication_date(soup):
    """提取发布日期"""
    # 尝试多种日期格式和位置
    date_patterns = [
        r'发布时间[:：]\s*(\d{4}-\d{2}-\d{2})',
        r'发布日期[:：]\s*(\d{4}-\d{2}-\d{2})',
        r'时间[:：]\s*(\d{4}-\d{2}-\d{2})'
    ]
    
    text = soup.get_text()
    for pattern in date_patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1)
    
    return "未知日期"

def extract_source(soup):
    """提取来源部门"""
    source_patterns = [
        r'来源[:：]\s*([^\s，。]+)',
        r'发布单位[:：]\s*([^\s，。]+)'
    ]
    
    text = soup.get_text()
    for pattern in source_patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1)
    
    return "国家卫健委"

if __name__ == "__main__":
    crawl_nhc_policies_with_content()
