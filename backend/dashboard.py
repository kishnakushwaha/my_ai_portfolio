import streamlit as st
import os
import shutil
import glob
from bs4 import BeautifulSoup
import subprocess
import datetime
import re

# Page Config
st.set_page_config(page_title="AI Portfolio CMS", layout="wide", page_icon="⚡")

# --- PATHS ---
# logic: dashboard.py is in backend/, so we go up one level for root
BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(BACKEND_DIR)

PATHS = {
    "public_articles": os.path.join(ROOT_DIR, "articles"),
    "draft_articles": os.path.join(BACKEND_DIR, "drafts", "articles"),
    "public_projects": os.path.join(ROOT_DIR, "projects"),
    "draft_projects": os.path.join(BACKEND_DIR, "drafts", "projects"),
    "template": os.path.join(ROOT_DIR, "articles", "template.html"),
    "index": os.path.join(ROOT_DIR, "index.html"),
    "search_script": os.path.join(ROOT_DIR, "generate_search_index.py")
}

# Ensure draft dirs exist
os.makedirs(PATHS["draft_articles"], exist_ok=True)
os.makedirs(PATHS["draft_projects"], exist_ok=True)

# --- HELPER FUNCTIONS ---

def get_files(directory, extension="*.html"):
    return glob.glob(os.path.join(directory, extension))

def move_file(src, dst_dir):
    filename = os.path.basename(src)
    dst = os.path.join(dst_dir, filename)
    shutil.move(src, dst)
    return dst

def set_visibility(file_path, status):
    """
    Status: 'public' (normal), 'unlisted' (meta tag), 'private' (move to drafts)
    """
    # 1. Handle Private (Move to drafts)
    if status == 'private':
        # Check if already in drafts
        if "drafts" in file_path: return
        # Move to drafts
        if "articles" in file_path:
            move_file(file_path, PATHS["draft_articles"])
        elif "projects" in file_path:
            move_file(file_path, PATHS["draft_projects"])
        return

    # 2. Handle Public/Unlisted (Must be in public folder)
    target_path = file_path
    if "drafts" in file_path:
        # Move back to public first
        if "articles" in file_path:
            target_path = move_file(file_path, PATHS["public_articles"])
        elif "projects" in file_path:
            target_path = move_file(file_path, PATHS["public_projects"])

    # 3. Update Meta Tag for Unlisted
    with open(target_path, 'r', encoding='utf-8') as f:
        soup = BeautifulSoup(f, 'html.parser')

    # Find or create visibility meta
    meta_vis = soup.find('meta', attrs={'name': 'visibility'})
    
    if status == 'unlisted':
        if not meta_vis:
            new_meta = soup.new_tag('meta', attrs={'name': 'visibility', 'content': 'unlisted'})
            soup.head.append(new_meta)
        else:
            meta_vis['content'] = 'unlisted'
    else: # public
        if meta_vis:
            meta_vis.decompose() # Remove tag to make it standard public

    with open(target_path, 'w', encoding='utf-8') as f:
        f.write(str(soup))

def create_article(title, description, date, content_html, category="Article"):
    # Read Template
    with open(PATHS["template"], 'r', encoding='utf-8') as f:
        template = f.read()

    # Simple Slug
    slug = re.sub(r'[^a-z0-9]+', '-', title.lower()).strip('-') + ".html"
    
    # Inject Content
    soup = BeautifulSoup(template, 'html.parser')
    
    # Title
    soup.title.string = f"{title} | Kishna Kushwaha"
    
    # H1
    h1 = soup.find('h1')
    if h1: h1.string = title
    
    # Meta Description
    meta_desc = soup.find('meta', attrs={'name': 'description'})
    if meta_desc: meta_desc['content'] = description

    # Date
    meta_date = soup.find(class_='article-meta-small')
    if meta_date: meta_date.string = f"{date} • 5 min read"

    # Navigation (Fix links to point to ../)
    # The template already has ../ links, so we represent the article as being in articles/ folder
    
    # Body Content (Find 'Paragraph text goes here...')
    # We replace the entire article body content area except the H1 and Meta
    article_body = soup.find(class_='article-body')
    if article_body:
        # Keep H1 and Meta
        h1_tag = article_body.find('h1')
        meta_tag = article_body.find(class_='article-meta-small')
        
        # Clear everything
        article_body.clear()
        
        # Re-add Header
        if h1_tag: article_body.append(h1_tag)
        if meta_tag: article_body.append(meta_tag)
        
        # Add New Content
        content_soup = BeautifulSoup(content_html, 'html.parser')
        article_body.append(content_soup)

    # Save to Drafts by default
    save_path = os.path.join(PATHS["draft_articles"], slug)
    with open(save_path, 'w', encoding='utf-8') as f:
        f.write(str(soup)) # formatting not strict

    return save_path

def toggle_section(section_id, hide=True):
    with open(PATHS["index"], 'r', encoding='utf-8') as f:
        soup = BeautifulSoup(f, 'html.parser')
        
    section = soup.find(id=section_id)
    if section:
        if hide:
            section['style'] = "display: none !important;"
        else:
            # Remove style or set to block
             del section['style']
             
    with open(PATHS["index"], 'w', encoding='utf-8') as f:
        f.write(str(soup))

def run_git_push():
    try:
        subprocess.run(["git", "add", "."], cwd=ROOT_DIR, check=True)
        subprocess.run(["git", "commit", "-m", "CMS Update: Content changes"], cwd=ROOT_DIR, check=True)
        subprocess.run(["git", "push"], cwd=ROOT_DIR, check=True)
        return True, "Successfully pushed to GitHub!"
    except Exception as e:
        return False, str(e)

def run_search_index():
    try:
        subprocess.run(["python3", "generate_search_index.py"], cwd=ROOT_DIR, check=True)
        return True, "Index Updated!"
    except Exception as e:
        return False, str(e)

def backup_drafts():
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    backup_dir = os.path.join(BACKEND_DIR, "backups")
    os.makedirs(backup_dir, exist_ok=True)
    
    # Zip the drafts folder
    archive_name = os.path.join(backup_dir, f"drafts_backup_{timestamp}")
    try:
        shutil.make_archive(archive_name, 'zip', PATHS["draft_articles"])
        # Also zip projects
        shutil.make_archive(archive_name + "_projects", 'zip', PATHS["draft_projects"])
        return True, f"Backup created: {os.path.basename(archive_name)}.zip"
    except Exception as e:
        return False, str(e)

# --- UI ---

st.title("⚡ AI Portfolio Dashboard")

tabs = st.tabs(["📄 Articles", "🚀 Projects", "🎨 Sections & Menu", "📝 New Content", "⚙️ Deploy & Backup"])

# --- TAB 1: ARTICLES ---
# ... (rest of code) ...

# --- TAB 5: DEPLOY ---
with tabs[4]:
    st.header("Deployment & Config")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.subheader("1. Update Search")
        st.caption("Run this after changing visibility.")
        if st.button("Generate Search Index"):
            ok, msg = run_search_index()
            if ok: st.success(msg)
            else: st.error(msg)
            
    with col2:
        st.subheader("2. Backup Drafts")
        st.caption("Zip all private drafts locally.")
        if st.button("Backup Data 💾"):
             ok, msg = backup_drafts()
             if ok: st.success(msg)
             else: st.error(msg)
             
    with col3:
        st.subheader("3. Push to GitHub")
        st.caption("Make your changes live.")
        if st.button("Deploy to Website 🚀"):
            with st.spinner("Pushing to GitHub..."):
                ok, msg = run_git_push()
                if ok: st.success(msg)
                else: st.error(msg)

    st.divider()
    st.info("Run this dashboard locally with: `streamlit run backend/dashboard.py`")
