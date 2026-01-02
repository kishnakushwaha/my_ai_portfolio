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
    files = glob.glob(os.path.join(directory, extension))
    return sorted(files)

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

    # Body Content
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
        f.write(str(soup))

    return save_path

def toggle_section(section_id, hide=True):
    with open(PATHS["index"], 'r', encoding='utf-8') as f:
        soup = BeautifulSoup(f, 'html.parser')
        
    section = soup.find(id=section_id)
    if section:
        if hide:
            section['style'] = "display: none !important;"
        else:
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

# DEBUG INFO (Remove later)
with st.expander("Debug: Check Paths"):
    st.write(f"**Root Dir:** `{ROOT_DIR}`")
    st.write(f"**Articles Dir:** `{PATHS['public_articles']}` (Exists: {os.path.exists(PATHS['public_articles'])})")
    st.write(f"**Files Found:** {len(get_files(PATHS['public_articles']))}")

tabs = st.tabs(["📄 Articles", "🚀 Projects", "🎨 Sections & Menu", "📝 New Content", "⚙️ Deploy & Backup"])

# --- TAB 1: ARTICLES ---
with tabs[0]:
    st.header("Manage Articles")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("🟢 Public / Unlisted")
        public_files = get_files(PATHS["public_articles"])
        for p in public_files:
            if "template.html" in p: continue
            name = os.path.basename(p)
            
            # Check visibility
            is_unlisted = False
            with open(p, 'r') as f:
                if 'content="unlisted"' in f.read():
                    is_unlisted = True
            
            status_icon = "🟡" if is_unlisted else "🟢"
            
            with st.expander(f"{status_icon} {name}"):
                c1, c2, c3 = st.columns(3)
                if c1.button("Make Public", key=f"pub_{name}"):
                    set_visibility(p, 'public')
                    st.rerun()
                if c2.button("Make Unlisted", key=f"unl_{name}"):
                    set_visibility(p, 'unlisted')
                    st.rerun()
                if c3.button("Move to Drafts 🔴", key=f"pvt_{name}"):
                    set_visibility(p, 'private')
                    st.rerun()

    with col2:
        st.subheader("🔴 Drafts (Private)")
        draft_files = get_files(PATHS["draft_articles"])
        for d in draft_files:
            name = os.path.basename(d)
            st.write(f"📄 {name}")
            if st.button("Publish 🟢", key=f"pub_draft_{name}"):
                set_visibility(d, 'public')
                st.rerun()

def toggle_project_card(file_path, card_title, hide=True):
    with open(file_path, 'r', encoding='utf-8') as f:
        soup = BeautifulSoup(f, 'html.parser')
    
    # Find all article cards
    cards = soup.find_all('article', class_='article-card')
    found = False
    
    for card in cards:
        h3 = card.find('h3')
        if h3 and h3.get_text(strip=True) == card_title:
             if hide:
                 card['style'] = "display: none !important;"
             else:
                 if 'style' in card.attrs:
                     del card['style']
             found = True
             break
             
    if found:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(str(soup))
        return True
    return False

def get_project_cards(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        soup = BeautifulSoup(f, 'html.parser')
    
    cards = soup.find_all('article', class_='article-card')
    project_list = []
    
    for card in cards:
        h3 = card.find('h3')
        a_tag = card.find('a', class_='article-read-btn')
        
        if h3:
            title = h3.get_text(strip=True)
            is_hidden = 'display: none' in card.get('style', '')
            
            # Resolve Target File
            target_path = None
            if a_tag and a_tag.get('href'):
                href = a_tag.get('href')
                # Handle relative links like ../articles/foo.html
                if href.startswith('../'):
                    # clean path
                    clean_rel = href.replace('../', '')
                    # check public loc
                    pot_path = os.path.join(ROOT_DIR, clean_rel)
                    target_path = pot_path
            
            project_list.append({
                "title": title,
                "hidden": is_hidden,
                "target": target_path
            })
            
    return project_list

def manage_project_item(ml_page, title, target_file, action):
    # 1. Update Card Visibility in HTML
    hide_card = (action != 'public') # Hide for unlisted and private
    toggle_project_card(ml_page, title, hide=hide_card)
    
    # 2. Update File Visibility (if target exists or is in drafts)
    if not target_file: return
    
    # Detect if file is currently in drafts to find it
    fname = os.path.basename(target_file)
    draft_path = os.path.join(PATHS["draft_articles"], fname)
    public_path = target_file
    
    # Check where the file really is right now
    real_path = public_path
    if not os.path.exists(public_path) and os.path.exists(draft_path):
        real_path = draft_path
    
    if os.path.exists(real_path):
        set_visibility(real_path, action)

# --- TAB 2: PROJECTS ---
with tabs[1]:
    st.header("Manage Projects")
    
    col1, col2 = st.columns(2)
    
    # 1. Page Level Control
    with col1:
        st.subheader("📂 Project Pages (Files)")
        public_projs = get_files(PATHS["public_projects"])
        for p in public_projs:
            name = os.path.basename(p)
            with st.expander(f"🟢 {name}"):
                if st.button("Move to Drafts 🔴", key=f"proj_pvt_{name}"):
                    set_visibility(p, 'private')
                    st.rerun()

    # 2. Individual ML Projects Control
    with col2:
        st.subheader("🧩 Machine Learning Projects (Items)")
        ml_page = os.path.join(PATHS["public_projects"], "machine_learning.html")
        
        if os.path.exists(ml_page):
            cards = get_project_cards(ml_page)
            if not cards:
                st.info("No project cards found in machine_learning.html")
            
            for item in cards:
                title = item['title']
                is_hidden = item['hidden']
                target = item['target']
                
                # Determine Visual Status
                status_icon = "�"
                if is_hidden: status_icon = "�" # Hidden or Draft
                # Check if unlisted meta exists in target
                if target and os.path.exists(target):
                     with open(target, 'r') as f:
                        if 'content="unlisted"' in f.read():
                            status_icon = "🟡"
                
                with st.expander(f"{status_icon} {title}"):
                    c1, c2, c3 = st.columns(3)
                    
                    if c1.button("Make Public", key=f"c_pub_{title}"):
                        manage_project_item(ml_page, title, target, 'public')
                        st.rerun()
                        
                    if c2.button("Make Unlisted", key=f"c_unl_{title}"):
                        manage_project_item(ml_page, title, target, 'unlisted')
                        st.rerun()
                        
                    if c3.button("Move to Drafts 🔴", key=f"c_drf_{title}"):
                        manage_project_item(ml_page, title, target, 'private')
                        st.rerun()
        else:
            st.warning("machine_learning.html not found!")

    st.divider()

# --- TAB 3: SECTIONS ---
with tabs[2]:
    st.header("Homepage Sections")
    
    # Read index to check current state
    with open(PATHS["index"], 'r') as f:
        index_html = f.read()
    
    sections = {
        "projects": "Guided Projects Section",
        "articles": "Latest Articles Section",
        "courses": "Recommended Resources"
    }
    
    for sec_id, label in sections.items():
        # Check if currently hidden
        is_hidden = f'id="{sec_id}"' in index_html and 'style="display: none !important;"' in index_html
        
        st.write(f"**{label}**")
        if is_hidden:
            if st.button(f"Show {label}", key=f"show_{sec_id}"):
                toggle_section(sec_id, hide=False)
                st.rerun()
        else:
            if st.button(f"Hide {label}", key=f"hide_{sec_id}"):
                toggle_section(sec_id, hide=True)
                st.rerun()
        st.divider()

# --- TAB 4: NEW CONTENT ---
with tabs[3]:
    st.header("Write New Article")
    
    new_title = st.text_input("Title")
    new_desc = st.text_area("Description (for SEO and Cards)")
    new_date = st.date_input("Date", datetime.date.today())
    
    # Markdown Editor
    new_content = st.text_area("Content (Markdown supported)", height=400)
    
    if st.button("Create Draft"):
        if new_title and new_content:
            try:
                import markdown
                html_content = markdown.markdown(new_content)
            except:
                html_content = f"<p>{new_content}</p>"
            
            save_path = create_article(new_title, new_desc, new_date.strftime("%b %d, %Y"), html_content)
            st.success(f"Draft created at {save_path}")
        else:
            st.error("Please fill title and content")

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
