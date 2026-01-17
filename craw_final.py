import requests
from bs4 import BeautifulSoup
import json
import time
import re
import csv
from urllib.parse import urljoin
import os

def load_websites_from_file(filename="websites.txt"):
    """从文件加载网站列表"""
    websites = []
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                # 跳过空行和注释
                if line and not line.startswith('#'):
                    websites.append(line)
        print(f"从 {filename} 加载了 {len(websites)} 个网站")
        return websites
    except FileNotFoundError:
        print(f"错误：找不到文件 {filename}")
        return []
    except Exception as e:
        print(f"读取网站列表文件时出错: {e}")
        return []

def crawl_multiple_websites():
    """爬取多个网站的政策信息"""
    
    # 加载网站列表
    websites = load_websites_from_file()
    if not websites:
        print("没有找到可用的网站列表，程序退出")
        return
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    }
    
    all_policy_data = []
    total_policies_crawled = 0
    
    # 遍历每个网站
    for website_index, list_url in enumerate(websites, 1):
        print(f"\n{'='*60}")
        print(f"开始爬取第 {website_index}/{len(websites)} 个网站: {list_url}")
        print(f"{'='*60}")
        
        policy_data = []
        
        try:
            # 爬取列表页
            response = requests.get(list_url, headers=headers, timeout=15)
            response.raise_for_status()
            response.encoding = 'utf-8'
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 提取政策链接 - 使用更通用的方法
            policy_links = extract_policy_links(soup, list_url)
            print(f"从该网站找到 {len(policy_links)} 个政策链接")
            
            if not policy_links:
                print("⚠️ 未找到政策链接，跳过该网站")
                continue
            
            # 第二级：逐个爬取政策详情内容
            for i, policy in enumerate(policy_links):
                if total_policies_crawled >= 1000:  # 如果已经达到1000条，停止爬取
                    print("已达到1000条数据目标，停止爬取")
                    break
                    
                try:
                    print(f"正在爬取第 {i+1}/{len(policy_links)} 个政策: {policy['title'][:50]}...")
                    
                    # 爬取详情页
                    detail_response = requests.get(policy['url'], headers=headers, timeout=20)
                    detail_response.encoding = 'utf-8'
                    
                    if detail_response.status_code == 200:
                        detail_soup = BeautifulSoup(detail_response.text, 'html.parser')
                        
                        # 提取政策内容
                        content = extract_policy_content(detail_soup)
                        pub_date = extract_publication_date(detail_soup)
                        source = extract_source(detail_soup, list_url)  # 根据URL判断来源
                        
                        policy_info = {
                            'title': policy['title'],
                            'url': policy['url'],
                            'publication_date': pub_date,
                            'source': source,
                            'website': list_url,  # 记录来源网站
                            'content': content,
                            'content_length': len(content),
                            'crawl_time': time.strftime('%Y-%m-%d %H:%M:%S')
                        }
                        
                        policy_data.append(policy_info)
                        total_policies_crawled += 1
                        print(f"✓ 成功爬取内容，长度: {len(content)} 字符，累计: {total_policies_crawled} 条")
                        
                    else:
                        print(f"✗ 无法访问页面: {detail_response.status_code}")
                    
                    # 礼貌延迟，避免请求过快
                    time.sleep(1)
                    
                except Exception as e:
                    print(f"✗ 爬取单个政策失败: {e}")
                    continue
            
            # 将该网站的政策数据添加到总数据中
            all_policy_data.extend(policy_data)
            print(f"✅ 完成该网站爬取，获得 {len(policy_data)} 条政策")
            
            # 保存当前进度（每个网站爬取后都保存一次）
            save_progress(all_policy_data, website_index)
            
            if total_policies_crawled >= 1000:
                print("🎯 已达到1000条数据目标！")
                break
                
        except Exception as e:
            print(f"❌ 爬取网站 {list_url} 时出错: {e}")
            continue
    
    # 最终保存所有数据
    if all_policy_data:
        save_final_data(all_policy_data)
        print(f"\n🎉 爬取完成！总共爬取了 {len(all_policy_data)} 条政策信息")
    else:
        print("未找到任何政策内容")

def extract_policy_links(soup, base_url):
    """提取政策链接，支持多种网站结构"""
    policy_links = []
    
    # 尝试多种可能的选择器
    link_selectors = [
        'a[href*=".shtml"]',
        'a[href*=".html"]',
        'li a',
        '.list a',
        '.news-list a',
        '.content a'
    ]
    
    for selector in link_selectors:
        links = soup.select(selector)
        for link in links:
            try:
                href = link.get('href', '')
                title = link.get_text().strip()
                
                if (href and title and 
                    len(title) > 5 and 
                    any(keyword in title for keyword in ['通知', '公告', '指南', '办法', '规定', '意见', '方案', '政策', '解读'])):
                    
                    # 补全链接
                    full_url = urljoin(base_url, href)
                    
                    policy_links.append({
                        'title': title,
                        'url': full_url
                    })
            except:
                continue
        
        if policy_links:  # 如果找到链接，就使用这个选择器
            break
    
    return policy_links

def extract_source(soup, website_url):
    """增强版来源提取函数：通过URL智能识别全国卫健委网站来源"""
    
    # 首先尝试从页面元数据中提取来源
    meta_source = extract_source_from_meta(soup)
    if meta_source and meta_source != "未知来源":
        return clean_source_name(meta_source)
    
    # 全国卫健委网站域名关键词映射
    region_mapping = {
        # 国家层面
        'nhc.gov.cn': '国家卫健委',
        
        # 直辖市
        'beijing.gov.cn': '北京市卫健委',
        'sh.gov.cn': '上海市卫健委', 
        'tj.gov.cn': '天津市卫健委',
        'cq.gov.cn': '重庆市卫健委',
        
        # 省
        'hebei.gov.cn': '河北省卫健委',
        'shanxi.gov.cn': '山西省卫健委',
        'neimenggu.gov.cn': '内蒙古自治区卫健委',
        'nmg.gov.cn': '内蒙古自治区卫健委',
        'liaoning.gov.cn': '辽宁省卫健委',
        'ln.gov.cn': '辽宁省卫健委',
        'jl.gov.cn': '吉林省卫健委',
        'heilongjiang.gov.cn': '黑龙江省卫健委',
        'hlj.gov.cn': '黑龙江省卫健委',
        'jiangsu.gov.cn': '江苏省卫健委', 
        'js.gov.cn': '江苏省卫健委',
        'zhejiang.gov.cn': '浙江省卫健委',
        'zj.gov.cn': '浙江省卫健委',
        'ah.gov.cn': '安徽省卫健委',
        'fujian.gov.cn': '福建省卫健委',
        'fj.gov.cn': '福建省卫健委',
        'jiangxi.gov.cn': '江西省卫健委',
        'jx.gov.cn': '江西省卫健委',
        'shandong.gov.cn': '山东省卫健委',
        'sd.gov.cn': '山东省卫健委',
        'henan.gov.cn': '河南省卫健委',
        'ha.gov.cn': '河南省卫健委',
        'hubei.gov.cn': '湖北省卫健委',
        'hb.gov.cn': '湖北省卫健委',
        'hunan.gov.cn': '湖南省卫健委',
        'hn.gov.cn': '湖南省卫健委',
        'guangdong.gov.cn': '广东省卫健委',
        'gd.gov.cn': '广东省卫健委',
        'gx.gov.cn': '广西壮族自治区卫健委',
        'hainan.gov.cn': '海南省卫健委',
        'sc.gov.cn': '四川省卫健委',
        'guizhou.gov.cn': '贵州省卫健委',
        'gz.gov.cn': '贵州省卫健委',
        'yunnan.gov.cn': '云南省卫健委',
        'yn.gov.cn': '云南省卫健委',
        'xizang.gov.cn': '西藏自治区卫健委',
        'xz.gov.cn': '西藏自治区卫健委',
        'shaanxi.gov.cn': '陕西省卫健委',
        'sn.gov.cn': '陕西省卫健委',
        'gansu.gov.cn': '甘肃省卫健委',
        'gs.gov.cn': '甘肃省卫健委',
        'qinghai.gov.cn': '青海省卫健委',
        'qh.gov.cn': '青海省卫健委',
        'ningxia.gov.cn': '宁夏回族自治区卫健委',
        'nx.gov.cn': '宁夏回族自治区卫健委',
        'xinjiang.gov.cn': '新疆维吾尔自治区卫健委',
        'xj.gov.cn': '新疆维吾尔自治区卫健委',
        
        # 特别行政区
        'chp.gov.hk': '香港卫生防护中心',
        'health.gov.hk': '香港卫生署',
        'ssm.gov.mo': '澳门卫生局',
        'health.gov.mo': '澳门卫生局'
    }
    
    # 智能识别来源
    website_lower = website_url.lower()
    
    # 1. 精确匹配域名关键词
    for keyword, source_name in region_mapping.items():
        if keyword in website_lower:
            return source_name
    
    # 2. 模糊匹配：尝试从URL中提取地域信息
    domain_parts = website_lower.split('//')[-1].split('/')[0].split('.')
    if len(domain_parts) >= 2:
        # 常见的二级域名模式识别
        region_codes = {
            'bj': '北京', 'sh': '上海', 'tj': '天津', 'cq': '重庆',
            'heb': '河北', 'sx': '山西', 'nm': '内蒙古', 'ln': '辽宁',
            'jl': '吉林', 'hlj': '黑龙江', 'js': '江苏', 'zj': '浙江',
            'ah': '安徽', 'fj': '福建', 'jx': '江西', 'sd': '山东',
            'ha': '河南', 'hb': '湖北', 'hn': '湖南', 'gd': '广东',
            'gx': '广西', 'hi': '海南', 'sc': '四川', 'gz': '贵州',
            'yn': '云南', 'xz': '西藏', 'sn': '陕西', 'gs': '甘肃',
            'qh': '青海', 'nx': '宁夏', 'xj': '新疆'
        }
        
        for part in domain_parts:
            if part in region_codes:
                # 判断是省还是直辖市
                region = region_codes[part]
                if region in ['北京', '上海', '天津', '重庆']:
                    return f'{region}市卫健委'
                else:
                    return f'{region}省卫健委'
    
    # 3. 最终回退方案
    return "国家卫健委"

def extract_source_from_meta(soup):
    """从页面meta标签中尝试提取来源信息"""
    meta_selectors = [
        'meta[name="source"]',
        'meta[name="origin"]',
        'meta[name="publisher"]',
        'meta[property="og:site_name"]'
    ]
    
    for selector in meta_selectors:
        meta_tag = soup.select_one(selector)
        if meta_tag and meta_tag.get('content'):
            content = meta_tag['content'].strip()
            if content and len(content) < 100:
                return content
    return "未知来源"

def clean_source_name(source_name):
    """清洗和标准化来源名称"""
    if not source_name:
        return "未知来源"
    
    # 移除常见干扰字符
    clean_name = re.sub(r'[【】\[\]<>（）()|&nbsp;]', '', source_name.strip())
    
    # 标准化名称
    standardization_map = {
        '卫生健康委员会': '卫健委',
        '卫生健康委': '卫健委',
        '卫生和计划生育委员会': '卫健委',
        '卫生局': '卫健委',
        '卫生厅': '卫健委',
        '卫生健康厅': '卫健委'
    }
    
    for old, new in standardization_map.items():
        clean_name = clean_name.replace(old, new)
    
    return clean_name

def save_progress(policy_data, website_index):
    """保存爬取进度"""
    if policy_data:
        # 保存进度文件
        progress_file = f'progress_after_website_{website_index}.json'
        with open(progress_file, 'w', encoding='utf-8') as f:
            json.dump(policy_data, f, ensure_ascii=False, indent=2)
        print(f"💾 进度已保存到: {progress_file}")

def save_final_data(policy_data):
    """保存最终数据"""
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    
    # 保存为JSON
    json_file = f'policies_all_websites_{timestamp}.json'
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(policy_data, f, ensure_ascii=False, indent=2)
    
    # 保存为CSV摘要
    csv_file = f'policies_summary_{timestamp}.csv'
    with open(csv_file, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        writer.writerow(['标题', '链接', '发布日期', '来源', '网站', '内容长度', '爬取时间'])
        for policy in policy_data:
            writer.writerow([
                policy['title'][:100] + '...' if len(policy['title']) > 100 else policy['title'],
                policy['url'],
                policy['publication_date'],
                policy['source'],
                policy['website'],
                policy['content_length'],
                policy['crawl_time']
            ])
    
    # 保存为TXT
    txt_file = f'policy_contents_{timestamp}.txt'
    with open(txt_file, 'w', encoding='utf-8') as f:
        for i, policy in enumerate(policy_data, 1):
            f.write(f"【第{i}条】{policy['title']}\n")
            f.write(f"【链接】{policy['url']}\n")
            f.write(f"【日期】{policy['publication_date']}\n")
            f.write(f"【来源】{policy['source']}\n")
            f.write(f"【网站】{policy['website']}\n")
            f.write(f"【内容】\n{policy['content']}\n")
            f.write("="*100 + "\n\n")
    
    print(f"📊 最终数据文件:")
    print(f"   JSON: {json_file}")
    print(f"   CSV: {csv_file}")
    print(f"   TXT: {txt_file}")

# 原有的 extract_policy_content, extract_publication_date 函数保持不变
def extract_policy_content(soup):
    """提取政策正文内容"""
    content_selectors = [
        'div.content',
        'div.TRS_Editor',
        'div.article-content',
        'div.text',
        'div#content',
        'div.main-content',
        '.article-content',
        '.content-main'
    ]
    
    for selector in content_selectors:
        content_div = soup.select_one(selector)
        if content_div:
            for elem in content_div(['script', 'style', 'nav', 'header', 'footer']):
                elem.decompose()
            text = content_div.get_text(separator='\n', strip=True)
            if len(text) > 100:
                return text
    
    body = soup.find('body')
    if body:
        for elem in body(['script', 'style', 'nav', 'header', 'footer', 'aside']):
            elem.decompose()
        return body.get_text(separator='\n', strip=True)
    
    return "无法提取内容"

def extract_publication_date(soup):
    """提取发布日期"""
    date_patterns = [
        r'发布时间[:：]\s*(\d{4}-\d{2}-\d{2})',
        r'发布日期[:：]\s*(\d{4}-\d{2}-\d{2})',
        r'时间[:：]\s*(\d{4}-\d{2}-\d{2})',
        r'发表时间[:：]\s*(\d{4}-\d{2}-\d{2})'
    ]
    
    text = soup.get_text()
    for pattern in date_patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1)
    
    return "未知日期"

if __name__ == "__main__":
    crawl_multiple_websites()