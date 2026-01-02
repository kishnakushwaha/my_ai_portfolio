import os
import json
import glob
import datetime
import math
from bs4 import BeautifulSoup

# Constants
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ARTICLES_DIR = os.path.join(BASE_DIR, 'articles')
PROJECTS_FILE = os.path.join(BASE_DIR, 'projects', 'machine_learning.html')
OUTPUT_FILE = os.path.join(BASE_DIR, 'search.json')
TEMPLATE_FILE = os.path.join(BASE_DIR, 'articles.html')

COLORS = [
    "linear-gradient(135deg, #2563EB, #1E40AF)",   # Blue
    "linear-gradient(135deg, #10B981, #059669)",   # Green
    "linear-gradient(135deg, #8B5CF6, #6D28D9)",   # Purple
    "linear-gradient(135deg, #F59E0B, #D97706)",   # Orange
    "linear-gradient(135deg, #EC4899, #DB2777)",   # Pink
    "linear-gradient(135deg, #14B8A6, #0F766E)",   # Teal
    "linear-gradient(135deg, #EF4444, #B91C1C)"    # Red
]
ICONS = ["fa-robot", "fa-brain", "fa-database", "fa-microchip", "fa-code", "fa-server", "fa-chart-network"]

def parse_date(date_str):
    try:
        # Expected format: "Oct 19, 2025" or similar
        # Cleanup: "Dec 18, 2025"
        clean_date = date_str.strip()
        return datetime.datetime.strptime(clean_date, "%b %d, %Y")
    except Exception as e:
        return datetime.datetime.min # Return min date if parse fails

def parse_article(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        soup = BeautifulSoup(f, 'html.parser')

    # Check Key Visibility
    meta_vis = soup.find('meta', attrs={'name': 'visibility'})
    if meta_vis and meta_vis.get('content') == 'unlisted':
        return None

    title_tag = soup.title
    title = title_tag.string.split('|')[0].strip() if title_tag else "Untitled Article"
    
    # Try to find description meta tag
    description = ""
    meta_desc = soup.find('meta', attrs={'name': 'description'})
    if meta_desc and meta_desc['content'] != "Article Description":
        description = meta_desc['content']
    
    # Fallback to first paragraph if no meta description
    article_body = soup.find('article', class_='article-body') or soup.find('div', class_='article-body') or soup.find('div', class_='entry-content')
    
    if not description and article_body:
        first_p = article_body.find('p')
        if first_p:
            text = first_p.get_text().strip()
            if len(text) < 20: 
                next_p = first_p.find_next('p')
                if next_p: text = next_p.get_text().strip()
            description = text[:150] + "..." if len(text) > 150 else text

    # Extract Image
    image_url = ""
    if article_body:
        imgs = article_body.find_all('img')
        for img in imgs:
            if img.get('src'):
                if 'icon' in img.get('src', '').lower(): continue
                image_url = img['src']
                break
        if not image_url:
            img = article_body.find('figure')
            if img and img.find('img'):
                image_url = img.find('img')['src']

        if image_url:
            # Handle relative paths for search context
            # Articles are in articles/, but search runs from root.
            # Local assets: "../assets/..." -> "assets/..."
            if image_url.startswith('../'):
                image_url = image_url[3:]
    
    # formatted date
    date_str = ""
    date_span = soup.find('span', class_='article-meta-small')
    if not date_span: date_span = soup.find('div', class_='article-meta-small')
    if date_span:
        date_str = date_span.get_text().strip().split('•')[0].strip()
    
    date_obj = parse_date(date_str)
    rel_path = os.path.relpath(file_path, BASE_DIR)
    
    # Deterministic visual assignment based on title hash
    hash_val = sum(ord(c) for c in title)
    color = COLORS[hash_val % len(COLORS)]
    icon = ICONS[hash_val % len(ICONS)]

    return {
        "title": title,
        "description": description,
        "url": rel_path,
        "category": "Article",
        "date_str": date_str,
        "date_obj": date_obj,
        "image": image_url,
        "color": color,
        "icon": icon,
        "link": f"articles/{os.path.basename(file_path)}"
    }

def generate_listings(articles):
    ARTICLES_PER_PAGE = 9
    
    # Use existing articles.html as template or backup
    if os.path.exists(TEMPLATE_FILE):
        with open(TEMPLATE_FILE, 'r', encoding='utf-8') as f:
            template_html = f.read()
    else:
        print("Error: articles.html not found to use as template.")
        return

    soup_clean = BeautifulSoup(template_html, 'html.parser')
    
    # Remove existing pagination from template
    existing_pag = soup_clean.find('div', style=lambda s: s and 'justify-content:center' in s)
    if existing_pag: existing_pag.decompose()
    
    base_listing_html = str(soup_clean)
    
    chunks = [articles[i:i + ARTICLES_PER_PAGE] for i in range(0, len(articles), ARTICLES_PER_PAGE)]
    if not chunks: chunks = [[]] # Handle empty case

    for page_num, chunk in enumerate(chunks, 1):
        soup = BeautifulSoup(base_listing_html, 'html.parser')
        grid = soup.find('div', class_='articles-grid')
        
        if grid:
            grid.clear() # Remove old entries
            
            for article in chunk:
                card_html = f"""
                <article class="article-card">
                    <div class="article-card-image">
                        <div class="placeholder-img" style="background: {article['color']};"></div>
                        <div class="blog-overlay"><i class="fas {article['icon']}"></i></div>
                    </div>
                    <div class="article-card-content">
                        <span class="article-meta-small">{article['date_str']}</span>
                        <h3>{article['title']}</h3>
                        <a href="{article['link']}" class="article-read-btn">Read Article</a>
                    </div>
                </article>
                """
                grid.append(BeautifulSoup(card_html, 'html.parser'))
            
            # Add Pagination
            pagination_div = soup.new_tag('div', style="display:flex; justify-content:center; gap:1rem; margin-top:3rem;")
            
            # Previous Link
            if page_num > 1:
                prev_link_files = "articles.html" if page_num == 2 else f"articles-{page_num-1}.html"
                a_prev = soup.new_tag('a', href=prev_link_files, **{'class': 'btn btn-secondary'})
                a_prev.string = "Previous"
                pagination_div.append(a_prev)
            
            # Page Info
            span = soup.new_tag('span', style="align-self:center; font-weight:600;")
            span.string = f"Page {page_num} of {len(chunks)}"
            pagination_div.append(span)
            
            # Next Link
            if page_num < len(chunks):
                next_link_files = f"articles-{page_num+1}.html"
                a_next = soup.new_tag('a', href=next_link_files, **{'class': 'btn btn-primary'})
                a_next.string = "Next"
                pagination_div.append(a_next)

            if grid.parent:
                # Remove any stray pagination
                for old_pag in grid.parent.find_all('div', style=lambda s: s and 'justify-content:center' in s):
                    old_pag.decompose()
                grid.parent.append(pagination_div)

        filename = "articles.html" if page_num == 1 else f"articles-{page_num}.html"
        output_path = os.path.join(BASE_DIR, filename)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(str(soup.prettify()))
        
        print(f"Generated {filename}")

def parse_projects():
    projects = []
    if os.path.exists(PROJECTS_FILE):
        projects.append({
            "title": "Machine Learning Projects",
            "description": "A collection of machine learning projects and case studies.",
            "url": "projects/machine_learning.html",
            "category": "Project",
            "date": ""
        })
    return projects

def main():
    print(f"Scanning articles in {ARTICLES_DIR}...")
    article_files = glob.glob(os.path.join(ARTICLES_DIR, '*.html'))
    
    valid_articles = []
    search_index = []

    for file_path in article_files:
        if file_path.endswith('template.html'):
            continue
            
        try:
            data = parse_article(file_path)
            if data and data['title'] not in ["Articles", "404 Not Found"]:
                valid_articles.append(data)
                
                # Prepare for search index (subset of data)
                search_index.append({
                    "title": data['title'],
                    "description": data['description'],
                    "url": data['url'],
                    "category": data['category'],
                    "date": data['date_str'],
                    "image": data['image']
                })
        except Exception as e:
            print(f"Error parsing {file_path}: {e}")

    # Sort Articles by Date Descending
    valid_articles.sort(key=lambda x: x['date_obj'], reverse=True)

    # Generate Listings
    generate_listings(valid_articles)

    # 2. Add Projects to Search Index
    search_index.extend(parse_projects())

    # 3. Add About Page
    search_index.append({
        "title": "About Kishna Kushwaha",
        "description": "Learn more about Kishna Kushwaha, an AI Engineer.",
        "url": "about.html",
        "category": "Page",
        "date": ""
    })

    # Save Search Index
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(search_index, f, indent=2)
    
    print(f"Generated {len(search_index)} items in search.json")

if __name__ == "__main__":
    main()
