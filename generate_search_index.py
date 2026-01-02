import os
import json
from bs4 import BeautifulSoup
import glob

# Constants
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ARTICLES_DIR = os.path.join(BASE_DIR, 'articles')
PROJECTS_FILE = os.path.join(BASE_DIR, 'projects', 'machine_learning.html')
OUTPUT_FILE = os.path.join(BASE_DIR, 'search.json')

def parse_article(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        soup = BeautifulSoup(f, 'html.parser')

    # Check Key Visibility
    meta_vis = soup.find('meta', attrs={'name': 'visibility'})
    if meta_vis and meta_vis.get('content') == 'unlisted':
        # Return a special marker or raising exception to skip
        return None

    title = soup.title.string.split('|')[0].strip() if soup.title else "Untitled Article"
    
    # Try to find description meta tag
    description = ""
    meta_desc = soup.find('meta', attrs={'name': 'description'})
    if meta_desc and meta_desc['content'] != "Article Description":
        description = meta_desc['content']
    
    # Fallback to first paragraph if no meta description or default
    article_body = soup.find('article', class_='article-body') or soup.find('div', class_='article-body') or soup.find('div', class_='entry-content')
    
    if not description and article_body:
        # Get first paragraph text
        first_p = article_body.find('p')
        if first_p:
            text = first_p.get_text().strip()
            # If text is too short or generic, try next p
            if len(text) < 20: 
                next_p = first_p.find_next('p')
                if next_p: text = next_p.get_text().strip()
            description = text[:150] + "..." if len(text) > 150 else text

    # Extract first image for thumbnail
    image_url = ""
    if article_body:
        # Find all images
        imgs = article_body.find_all('img')
        for img in imgs:
            if img.get('src'):
                # Skip small icons or invisible images if any
                if 'icon' in img.get('src', '').lower(): continue
                image_url = img['src']
                break
        
        # If still no image, try to find in figure
        if not image_url:
            img = article_body.find('figure')
            if img and img.find('img'):
                image_url = img.find('img')['src']

        if image_url:
            # Ensure relative path is correct for search context (which is root or ../)
            # The articles are in articles/, but search.js runs from root.
            # If src is "../assets/...", then from root it is "assets/..."
            if image_url.startswith('../'):
                image_url = image_url[3:] # Remove ../
    
    # formatted date
    date = ""
    date_span = soup.find('span', class_='article-meta-small') # Updated class name check
    if not date_span: date_span = soup.find('div', class_='article-meta-small')
    if date_span:
        date = date_span.get_text().strip().split('•')[0].strip()

    rel_path = os.path.relpath(file_path, BASE_DIR)

    return {
        "title": title,
        "description": description,
        "url": rel_path,
        "category": "Article",
        "date": date,
        "image": image_url
    }

def parse_projects():
    projects = []
    if not os.path.exists(PROJECTS_FILE):
        return projects

    with open(PROJECTS_FILE, 'r', encoding='utf-8') as f:
        soup = BeautifulSoup(f, 'html.parser')

    # Assuming projects are in cards. Adjust selector based on actual project HTML structure.
    # Looking at previous context, projects might be in .project-card or similar.
    # Let's try to find project cards. 
    # Based on index.html snippet, they might be anchors with class 'project-card'.
    # But in projects/machine_learning.html they might be different.
    # I'll guess a generic card structure or look for headings.
    
    # Let's just index the main project page for now, or specific project article files if they exist.
    # Reading task.md, user has 'projects/machine_learning.html'.
    
    # Let's index the page itself as a resource.
    projects.append({
        "title": "Machine Learning Projects",
        "description": "A collection of machine learning projects and case studies.",
        "url": "projects/machine_learning.html",
        "category": "Project",
        "date": ""
    })
    
    return projects

def main():
    search_index = []

    # 1. Index Articles
    print(f"Scanning articles in {ARTICLES_DIR}...")
    article_files = glob.glob(os.path.join(ARTICLES_DIR, '*.html'))
    for file_path in article_files:
        if file_path.endswith('template.html'):
            continue
        try:
            data = parse_article(file_path)
            if data and data['title'] not in ["Articles", "404 Not Found"]: # Skip non-content pages
                search_index.append(data)
        except Exception as e:
            print(f"Error parsing {file_path}: {e}")

    # 2. Index Projects (Basic)
    search_index.extend(parse_projects())

    # 3. Index Main Pages
    search_index.append({
        "title": "About Kishna Kushwaha",
        "description": "Learn more about Kishna Kushwaha, an AI Engineer.",
        "url": "about.html",
        "category": "Page",
        "date": ""
    })

    # Save to JSON
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(search_index, f, indent=2)
    
    print(f"Generated {len(search_index)} items in search.json")

if __name__ == "__main__":
    main()
