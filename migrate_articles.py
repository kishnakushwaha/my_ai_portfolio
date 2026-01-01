import requests
from bs4 import BeautifulSoup
import datetime
import os
import re

import json

# Load Configuration
try:
    with open('migration_sources.json', 'r') as f:
        config = json.load(f)
    GUIDED_PROJECTS = config.get('guided_projects', [])
    DISCOVERY_SEEDS = config.get('discovery_seeds', [])
    SOURCE_DOMAIN = config.get('source_domain', 'amanxai.com')
    ASSETS_PATH_SIG = config.get('assets_path', '/wp-content/uploads/')
except FileNotFoundError:
    print("Error: migration_sources.json not found. Please create it to define source URLs.")
    GUIDED_PROJECTS = []
    DISCOVERY_SEEDS = []
    SOURCE_DOMAIN = "amanxai.com"
    ASSETS_PATH_SIG = "/wp-content/uploads/"

# Combined Source for Crawling
SOURCE_ARTICLES = GUIDED_PROJECTS + DISCOVERY_SEEDS

# Read Template
with open('articles/template.html', 'r') as f:
    TEMPLATE_HTML = f.read()

# Helper to Generate Color Gradient for Card (Cycling)
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

def slugify(title):
    return re.sub(r'[^a-z0-9]+', '-', title.lower()).strip('-') + ".html"

import json

# Build URL Map for Internal Linking
URL_MAP = {}
for art in GUIDED_PROJECTS:
    # Key: plain URL, value: local relative path
    # Normalize URL end (strip slash) just in case
    clean_url = art['url'].rstrip('/')
    URL_MAP[clean_url] = slugify(art['title'])
    # Also Map original with slash
    URL_MAP[art['url']] = slugify(art['title'])

# Note: We don't map DISCOVERY_SEEDS to slugs because we don't necessarily want "home.html"

def fetch_and_clean_content(url):
    try:
        response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # AmanXAI uses .ct-entry-content or article body
        content_div = soup.find('div', class_='entry-content') or soup.find('article')
        
        if not content_div:
            return "<p>Content could not be fetched.</p>"
            
        # Clean up CodeMirror Blocks
        code_blocks = content_div.find_all(class_='wp-block-codemirror-blocks-code-block')
        for block in code_blocks:
            pre_tag = block.find('pre')
            if pre_tag:
                # Extract code content
                code_text = pre_tag.get_text()
                
                # Default language
                lang = 'python'
                
                # Try to find language in data-setting
                if pre_tag.get('data-setting'):
                    try:
                        settings = json.loads(pre_tag['data-setting'])
                        mode = settings.get('mode', 'python')
                        # Map mode to simple language name
                        if 'python' in mode: lang = 'python'
                        elif 'javascript' in mode or 'js' in mode: lang = 'javascript'
                        elif 'html' in mode: lang = 'html'
                        elif 'css' in mode: lang = 'css'
                        elif 'sql' in mode: lang = 'sql'
                        elif 'bash' in mode or 'shell' in mode: lang = 'bash'
                        else: lang = 'python' # Fallback
                    except:
                        pass
                
                # Create new structure: <pre><code class="language-python">...</code></pre>
                new_pre = soup.new_tag("pre")
                new_code = soup.new_tag("code", **{'class': f'language-{lang}'})
                new_code.string = code_text
                new_pre.append(new_code)
                
                # Replace the entire WP block with new pre
                block.replace_with(new_pre)

        # Remove unwanted elements
        for unwanted in content_div.select('.st-post-share, .jp-relatedposts, .widget-area, script, iframe'):
            unwanted.decompose()
            
        # Remove specific promotional text
        for p in content_div.find_all('p'):
            if "follow me on Instagram" in p.get_text() or "Hands-On GenAI" in p.get_text():
                p.decompose()

        # Fix Internal Links
        for a in content_div.find_all('a', href=True):
            original_href = a['href'].rstrip('/')
            match_slug = URL_MAP.get(original_href) or URL_MAP.get(a['href'])
            
            if match_slug:
                # Replace with local path
                a['href'] = match_slug

        return content_div.decode_contents()
    except Exception as e:
        print(f"Error fetching content: {e}")
        return "<p>Error loading content.</p>"

# PROCESSING QUEUE
# Convert initial list to a list of dicts we can process
processing_queue = [art for art in SOURCE_ARTICLES]
processed_urls = set() # To track unique URLs we have seen
migrated_content = {}  # Store title, content, date, etc. key=url

# Helper to fetch title if missing
def get_article_details(url):
    try:
        response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
        if response.status_code != 200: return None, None
        soup = BeautifulSoup(response.content, 'html.parser')
        
        title = soup.find('h1').get_text().strip() if soup.find('h1') else "Untitled Article"
        # Extract content block for cleaning
        content_div = soup.find('div', class_='entry-content') or soup.find('article')
        if not content_div: return title, None
        
        return title, content_div
    except:
        return None, None

print("Starting recursive migration...")

# Special Group Logic
PYTHON_PARENT_URL = "https://amanxai.com/2024/08/23/python-problems-for-coding-interviews/"
special_urls = set()
special_urls.add(PYTHON_PARENT_URL)
special_urls.add(PYTHON_PARENT_URL.rstrip('/'))

# Pre-fetch special group to identify children
print("identifying Python Interview sub-articles...")
try:
    resp = requests.get(PYTHON_PARENT_URL, headers={'User-Agent': 'Mozilla/5.0'})
    if resp.status_code == 200:
        p_soup = BeautifulSoup(resp.content, 'html.parser')
        p_div = p_soup.find('div', class_='entry-content') or p_soup.find('article')
        if p_div:
            for a in p_div.find_all('a', href=True):
                if 'amanxai.com' in a['href']:
                     special_urls.add(a['href'])
                     special_urls.add(a['href'].rstrip('/'))
except Exception as e:
    print(f"Warning: Could not pre-fetch special group: {e}")

max_articles = 150 # Safety limit
count = 0
count_special = 0

# Normal Date Cursor (From Today)
date_normal = datetime.date.today()
# Special Date Cursor (Requested Oct 25, 2025)
date_special = datetime.date(2025, 10, 25)

while processing_queue and count < max_articles:
    current_art = processing_queue.pop(0)
    url = current_art['url']
    
    # Normalize URL
    clean_url = url.rstrip('/')
    if clean_url in processed_urls:
        continue
        
    print(f"Processing ({count+1}): {current_art.get('title', 'Unknown Article')}")
    
    # --- FETCH LOGIC OMITTED FOR BREVITY, ASSUMED UNCHANGED UNTIL DATE ASSIGNMENT ---
    
    # Fetch Content
    if 'content_html' not in current_art:
        try:
            response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
            soup = BeautifulSoup(response.content, 'html.parser')
            
            content_div = soup.find('div', class_='entry-content') or soup.find('article')
            if not content_div:
                print("Skipping empty content...")
                continue

            if 'title' not in current_art:
                h1 = soup.find('h1')
                current_art['title'] = h1.get_text().strip() if h1 else "Untitled AI Article"

            for a in content_div.find_all('a', href=True):
                href = a['href']
                if SOURCE_DOMAIN in href and ('/2021/' in href or '/2022/' in href or '/2023/' in href or '/2024/' in href or '/2025/' in href):
                    check_url = href.rstrip('/')
                    if check_url not in processed_urls:
                         is_in_queue = any(q['url'].rstrip('/') == check_url for q in processing_queue)
                         if not is_in_queue:
                             processing_queue.append({'url': href})

            code_blocks = content_div.find_all(class_='wp-block-codemirror-blocks-code-block')
            for block in code_blocks:
                pre_tag = block.find('pre')
                if pre_tag:
                    code_text = pre_tag.get_text()
                    lang = 'python'
                    if pre_tag.get('data-setting'):
                        try:
                            settings = json.loads(pre_tag['data-setting'])
                            mode = settings.get('mode', 'python')
                            if 'python' in mode: lang = 'python'
                            elif 'javascript' in mode or 'js' in mode: lang = 'javascript'
                            elif 'html' in mode: lang = 'html'
                            elif 'css' in mode: lang = 'css'
                            elif 'sql' in mode: lang = 'sql'
                            else: lang = 'python'
                        except: pass
                    new_pre = soup.new_tag("pre")
                    new_code = soup.new_tag("code", **{'class': f'language-{lang}'})
                    new_code.string = code_text
                    new_pre.append(new_code)
                    block.replace_with(new_pre)

            for unwanted in content_div.select('.st-post-share, .jp-relatedposts, .widget-area, script, iframe'):
                unwanted.decompose()
            for p in content_div.find_all('p'):
                if "follow me on Instagram" in p.get_text() or "Hands-On GenAI" in p.get_text():
                    p.decompose()

            if 'description' not in current_art:
                first_p = content_div.find('p')
                if first_p:
                   text = first_p.get_text().strip().replace('"', "'")
                   current_art['description'] = text[:160] + "..." if len(text) > 160 else text
                else:
                   current_art['description'] = f"Learn more about {current_art['title']}."

            current_art['content_html'] = content_div.decode_contents()
            
        except Exception as e:
            print(f"Error processing article: {e}")
            continue

    processed_urls.add(clean_url)
    
    bad_titles = ["Untitled AI Article", "Oops! That page can’t be found.", "Page not found", "404 Not Found"]
    if current_art['title'] in bad_titles or "Oops!" in current_art['title']:
        print(f"Skipping invalid article: {current_art['title']}")
        continue

    slug = slugify(current_art['title'])
    
    # --- DATE ASSIGNMENT LOGIC ---
    if url in special_urls or clean_url in special_urls:
        # Special Group: Oct 25, 2025 start, 2 per day
        clean_date = date_special.strftime("%b %d, %Y")
        count_special += 1
        if count_special % 2 == 0:
            date_special -= datetime.timedelta(days=1)
    else:
        # Normal Group: Today start, 1 per day (or 2 per day if preferred, keeping original logic)
        clean_date = date_normal.strftime("%b %d, %Y")
        # Decrement distinct from special
        if count % 2 == 0: # Keeping user's general '2 per day' preference if that was the case
             date_normal -= datetime.timedelta(days=1)

    migrated_content[clean_url] = {
        'title': current_art['title'],
        'slug': slug,
        'date': clean_date,
        'content': current_art['content_html'],
        'color': COLORS[count % len(COLORS)],
        'icon': ICONS[count % len(ICONS)],
        'link': f"articles/{slug}"
    }
    
    migrated_content[url] = migrated_content[clean_url]
    
    count += 1

print(f"Total articles fetched: {len(migrated_content) // 2}") # Div 2 because double mapping

# PASS 2: REWRITE LINKS AND SAVE FILES
print("Rewriting links, adding navigation, and saving files...")

generated_articles = [] # List for pagination

# Get unique entries (values)
unique_entries = list({v['slug']: v for k, v in migrated_content.items()}.values())

for i, entry in enumerate(unique_entries):
    # Parse content again to rewrite links
    soup = BeautifulSoup(entry['content'], 'html.parser')
    
    # 1. First, Robust Link Rewriting (Articles)
    for a in soup.find_all('a', href=True):
        href = a['href'].rstrip('/')
        
        # Robust Match: Try exact, then normalized
        match = None
        if href in migrated_content:
            match = migrated_content[href]
        else:
            # Try swapping scheme
            if 'https://' in href: alt = href.replace('https://', 'http://')
            else: alt = href.replace('http://', 'https://')
            if alt in migrated_content: match = migrated_content[alt]
        
        if match:
             # Found a link to an article we migrated!
             local_slug = match['slug']
             a['href'] = local_slug 
             a['target'] = "" 
        elif 'amanxai.com' in href:
            # It's an amanxai link but NOT a migrated article (e.g. category, tag, or 404)
            # Disable it to prevent leaking to original site
            a['href'] = "#"
            a['style'] = "pointer-events: none; cursor: default; text-decoration: none; color: inherit;"
            a.attrs.pop('target', None)

    # 2. Scrub All Tags for Amanxai References (Images, Data Attributes)
    # Remove srcset to simplify image handling (browsers will use src)
    for tag in soup.find_all(attrs={'srcset': True}):
        del tag['srcset']
        
    for tag in soup.find_all(True): # All tags
        # Check all attributes
        attrs_to_remove = []
        for attr, val in tag.attrs.items():
            if isinstance(val, str) and 'amanxai.com' in val:
                # If it's src, we need to handle it (download)
                if attr == 'src':
                    continue # Handled in asset download loop below
                
                # If it's href, we handled it above (or will handle in asset loop)
                if attr == 'href':
                    continue
                    
                # For data-*, typically lightbox stuff, just remove
                attrs_to_remove.append(attr)
                
        for attr in attrs_to_remove:
            del tag[attr]

    final_content = soup.decode_contents()
    
    # Inject into Template
    new_html = TEMPLATE_HTML.replace('Article Title Goes Here', entry['title'])
    new_html = new_html.replace('Article Title | Kishna Kushwaha', f"{entry['title']} | Kishna Kushwaha")
    # Replace Meta Description
    desc = entry.get('description', 'Article Description')
    new_html = new_html.replace('content="Article Description"', f'content="{desc}"')
    # Replace default date
    new_html = re.sub(r'Dec \d+, 2025 • \d+ min read', f"{entry['date']} • 5 min read", new_html)
    
    # Inject body
    # We want to inject Top Navigation right after the meta data
    nav_html = """
    <!-- Navigation Top -->
    <div style="margin-bottom: 2rem; padding-bottom: 1rem; border-bottom: 1px solid #E5E7EB; display: flex; justify-content: space-between;">
        <a href="#" class="nav-prev" style="text-decoration: none; color: var(--primary-color); font-weight: 600;">&larr; Previous Article</a>
        <a href="../articles.html" style="text-decoration: none; color: var(--text-muted); font-weight: 500;">All Articles</a>
        <a href="#" class="nav-next" style="text-decoration: none; color: var(--primary-color); font-weight: 600;">Next Article &rarr;</a>
    </div>
    """
    
    meta_end_idx = new_html.find('min read</div>') + 14
    article_end_idx = new_html.find('</article>')
    
    # Insert Nav Top + Content
    final_html_str = new_html[:meta_end_idx] + f"\n\n{nav_html}\n\n{final_content}\n\n" + new_html[article_end_idx:]
    
    # Parse full page to update footer navigation robustly AND download assets
    full_soup = BeautifulSoup(final_html_str, 'html.parser')
    
    # ASSET DOWNLOAD LOGIC (Images AND Files)
    # Check both <a> (files) and <img> (images)
    targets = []
    for a in full_soup.find_all('a', href=True):
        targets.append((a, 'href'))
    for img in full_soup.find_all('img', src=True):
        targets.append((img, 'src'))
        
    for tag, attr in targets:
        url = tag[attr]
        
        # Check if it is an asset we want to host locally
        # 1. Files (.csv, .zip, etc)
        # 2. Images (amanxai.com/wp-content/uploads/...)
        
        is_source_asset = SOURCE_DOMAIN in url and ASSETS_PATH_SIG in url
        is_ext_file = any(url.lower().endswith(ext) for ext in ['.csv', '.zip', '.json']) and 'http' in url
        
        if is_source_asset or is_ext_file:
             # Skip some specific bad links
             if 'food-delivery-dataset' in url: continue
             
             # Extract filename
             # Remove query params
             clean_url_for_name = url.split('?')[0]
             filename = clean_url_for_name.split('/')[-1]
             
             # Decode if necessary (e.g. %20)
             import urllib.parse
             filename = urllib.parse.unquote(filename)
             
             local_dir = 'assets/datasets' # Keeping simple, can be assets/images if preferred but user path structure is flexible
             local_path = os.path.join(local_dir, filename)
             
             # Ensure dir exists (it should, but just in case)
             os.makedirs(local_dir, exist_ok=True)
             
             # Download if not exists
             if not os.path.exists(local_path):
                 try:
                     print(f"Downloading asset: {filename}")
                     headers = {
                         'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                         'Referer': 'https://amanxai.com/',
                         'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8'
                     }
                     # Clean URL for request (handle existing query params in original)
                     fetch_url = url.replace('&amp;', '&')
                     
                     r = requests.get(fetch_url, headers=headers, allow_redirects=True, timeout=10)
                     if r.status_code == 200:
                         with open(local_path, 'wb') as f:
                             f.write(r.content)
                     else:
                         print(f"Failed to download asset: Status {r.status_code}")
                 except Exception as e:
                     print(f"Error downloading asset: {e}")
             
             # FORCE rewrite link to local path
             tag[attr] = f"../{local_dir}/{filename}"
             
             # Remove 'rel' or 'target' for these local assets
             if 'target' in tag.attrs: del tag['target']
             if 'rel' in tag.attrs: del tag['rel']
             if 'srcset' in tag.attrs: del tag['srcset'] # Ensure srcset doesn't override new local src

    # Find navigation container (flex with space-between)
    # Update Navigation Links (Find ALL prev/next links)
    # Previous Link
    prev_slug = unique_entries[i+1]['slug'] if i + 1 < len(unique_entries) else "#"
    # Next Link
    next_slug = unique_entries[i-1]['slug'] if i > 0 else "#"
    
    # Bottom Nav is in template, Top Nav is injected.
    # Target by text content since we reuse the same text in both.
    for a in full_soup.find_all('a'):
        # Normalize whitespace (replace newlines and multiple spaces with single space)
        text = ' '.join(a.get_text().split())
        
        if "Previous Article" in text:
            a['href'] = prev_slug
            if prev_slug == "#": 
                a['style'] = (a.get('style', '') + '; color: #ccc; pointer-events: none;').strip(';')
            
        if "Next Article" in text:
            a['href'] = next_slug
            if next_slug == "#": 
                a['style'] = (a.get('style', '') + '; color: #ccc; pointer-events: none;').strip(';')

    # Save
    with open(f"articles/{entry['slug']}", 'w') as f:
        f.write(str(full_soup))
        
    generated_articles.append(entry)

print("Articles saved. Generating listing...")

# Pagination Logic
# Exclude Guided Projects from the main Articles list
# We use Slugs for robust filtering
project_slugs = set()
for p in GUIDED_PROJECTS:
    project_slugs.add(slugify(p['title']))

# Configure all generated_articles but filter out projects for the Listing Pages
listing_articles = [art for art in generated_articles if art['slug'] not in project_slugs]

ARTICLES_PER_PAGE = 9
chunks = [listing_articles[i:i + ARTICLES_PER_PAGE] for i in range(0, len(listing_articles), ARTICLES_PER_PAGE)]

# Read Listing Template - CLEAN IT FIRST
with open('articles.html', 'r') as f:
    LISTING_HTML = f.read()
    
# Clean any existing pagination from the template string itself to avoid accumulation
# parse once to find and remove default pagination if exists
soup_clean = BeautifulSoup(LISTING_HTML, 'html.parser')
existing_pag = soup_clean.find('div', style=lambda s: s and 'justify-content:center' in s)
if existing_pag: existing_pag.decompose()
base_listing_html = str(soup_clean)


for page_num, chunk in enumerate(chunks, 1):
    soup = BeautifulSoup(base_listing_html, 'html.parser')
    grid = soup.find('div', class_='articles-grid')
    if grid:
        grid.clear()
        
        for article in chunk:
            # Create card
            card_html = f"""
            <article class="article-card">
                <div class="article-card-image">
                    <div class="placeholder-img" style="background: {article.get('color', COLORS[0])};"></div>
                    <div class="blog-overlay"><i class="fas {article.get('icon', ICONS[0])}"></i></div>
                </div>
                <div class="article-card-content">
                    <span class="article-meta-small">{article['date']}</span>
                    <h3>{article['title']}</h3>
                    <a href="{article['link']}" class="article-read-btn">Read Article</a>
                </div>
            </article>
            """
            # Append as BS4 object
            grid.append(BeautifulSoup(card_html, 'html.parser'))
            
        # Add Pagination
        prev_link = f"articles-{page_num-1}.html" if page_num > 1 else "#"
        if page_num == 2: prev_link = "articles.html"
        next_link = f"articles-{page_num+1}.html" if page_num < len(chunks) else "#"
        
        pagination_div = soup.new_tag('div', style="display:flex; justify-content:center; gap:1rem; margin-top:3rem;")
        
        if prev_link != "#":
            a_prev = soup.new_tag('a', href=prev_link, **{'class': 'btn btn-secondary'})
            a_prev.string = "Previous"
            pagination_div.append(a_prev)
            
        span = soup.new_tag('span', style="align-self:center; font-weight:600;")
        span.string = f"Page {page_num} of {len(chunks)}"
        pagination_div.append(span)
        
        if next_link != "#":
            a_next = soup.new_tag('a', href=next_link, **{'class': 'btn btn-primary'})
            a_next.string = "Next"
            pagination_div.append(a_next)
               
        # Append pagination after grid
        # grid.parent is the section container
        if grid.parent:
            # Remove any existing pagination first (double safety)
            for old_pag in grid.parent.find_all('div', style=lambda s: s and 'justify-content:center' in s):
                old_pag.decompose()
            grid.parent.append(pagination_div)
            
    filename = "articles.html" if page_num == 1 else f"articles-{page_num}.html"
    with open(filename, 'w') as f:
        f.write(str(soup.prettify())) # Prettify for clean output
        
    print(f"Created listing page: {filename}")
            
    filename = "articles.html" if page_num == 1 else f"articles-{page_num}.html"
    with open(filename, 'w') as f:
        f.write(str(soup.prettify())) # Prettify for clean output
        
    print(f"Created listing page: {filename}")

print("Migration Complete.")
