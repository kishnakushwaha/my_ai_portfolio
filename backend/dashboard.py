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

import sys

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
        if "drafts" in file_path: return
        if "articles" in file_path:
            move_file(file_path, PATHS["draft_articles"])
        elif "projects" in file_path:
            move_file(file_path, PATHS["draft_projects"])
        return

    # 2. Handle Public/Unlisted (Must be in public folder)
    target_path = file_path
    if "drafts" in file_path:
        if "articles" in file_path:
            target_path = move_file(file_path, PATHS["public_articles"])
        elif "projects" in file_path:
            target_path = move_file(file_path, PATHS["public_projects"])

    # 3. Update Meta Tag for Unlisted
    with open(target_path, 'r', encoding='utf-8') as f:
        soup = BeautifulSoup(f, 'html.parser')

    meta_vis = soup.find('meta', attrs={'name': 'visibility'})
    
    if status == 'unlisted':
        if not meta_vis:
            new_meta = soup.new_tag('meta', attrs={'name': 'visibility', 'content': 'unlisted'})
            soup.head.append(new_meta)
        else:
            meta_vis['content'] = 'unlisted'
    else: # public
        if meta_vis:
            meta_vis.decompose() 

    with open(target_path, 'w', encoding='utf-8') as f:
        f.write(str(soup))
        
    # Validating/Updating site is now handled by the caller (process_bulk) via run_search_index

def create_article(title, description, date, content_html, category="Article"):
    with open(PATHS["template"], 'r', encoding='utf-8') as f:
        template = f.read()

    slug = re.sub(r'[^a-z0-9]+', '-', title.lower()).strip('-') + ".html"
    soup = BeautifulSoup(template, 'html.parser')
    
    soup.title.string = f"{title} | Kishna Kushwaha"
    h1 = soup.find('h1')
    if h1: h1.string = title
    
    meta_desc = soup.find('meta', attrs={'name': 'description'})
    if meta_desc: meta_desc['content'] = description

    meta_date = soup.find(class_='article-meta-small')
    if meta_date: meta_date.string = f"{date} • 5 min read"

    article_body = soup.find(class_='article-body')
    if article_body:
        h1_tag = article_body.find('h1')
        meta_tag = article_body.find(class_='article-meta-small')
        article_body.clear()
        if h1_tag: article_body.append(h1_tag)
        if meta_tag: article_body.append(meta_tag)
        content_soup = BeautifulSoup(content_html, 'html.parser')
        article_body.append(content_soup)

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
        # Configure Git Identity (Required for Streamlit Cloud / Containers)
        subprocess.run(["git", "config", "user.email", "kishnakushwaha91@gmail.com"], cwd=ROOT_DIR, check=False)
        subprocess.run(["git", "config", "user.name", "CMS Bot"], cwd=ROOT_DIR, check=False)
        
        # Force Remote URL with Username to prevent "could not read Username" prompt
        subprocess.run([
            "git", "remote", "set-url", "origin", 
            "https://kishnakushwaha91-afk@github.com/kishnakushwaha91-afk/my_ai_portfolio.git"
        ], cwd=ROOT_DIR, check=False)

        # --------------------------------------------------------------------------------
        # ROBUST AUTHENTICATION STRATEGY
        # --------------------------------------------------------------------------------
        # 1. Try to find the password using the available credential helper directly.
        #    This is necessary because Streamlit's environment often breaks 'git credential' path resolution.
        import glob
        git_password = None
        
        # Locate the helper
        found_helpers = glob.glob("/opt/homebrew/Cellar/git/*/libexec/git-core/git-credential-osxkeychain")
        if found_helpers:
            helper_path = found_helpers[-1]
            # Invoke helper to get credentials
            input_data = "protocol=https\nhost=github.com\nusername=kishnakushwaha91-afk\n"
            try:
                proc = subprocess.run([helper_path, "get"], input=input_data, text=True, capture_output=True, check=True)
                # Parse output for 'password=...'
                for line in proc.stdout.splitlines():
                    if line.startswith("password="):
                        git_password = line.split("=", 1)[1]
                        break
            except Exception as e:
                print(f"Auth Helper Failed: {e}")

        # 2. Configure Remote URL with Credentials (if found) or Username (fallback)
        if git_password:
            # INJECT CREDENTIALS: https://user:pass@github.com/...
            remote_url = f"https://kishnakushwaha91-afk:{git_password}@github.com/kishnakushwaha91-afk/my_ai_portfolio.git"
        else:
            # FALLBACK: Just username, hope for the best
            remote_url = "https://kishnakushwaha91-afk@github.com/kishnakushwaha91-afk/my_ai_portfolio.git"

        # Set the remote URL
        subprocess.run(["git", "remote", "set-url", "origin", remote_url], cwd=ROOT_DIR, check=False)

        # 3. Clean up config to avoid 'command not found' errors from bad previous attempts
        subprocess.run(["git", "config", "--unset", "credential.helper"], cwd=ROOT_DIR, check=False)
        # --------------------------------------------------------------------------------

        # Use capture_output=True to get error messages
        subprocess.run(["git", "add", "."], cwd=ROOT_DIR, check=True, capture_output=True)
        
        # Commit changes (handle "nothing to commit" case gracefully)
        commit_proc = subprocess.run(["git", "commit", "-m", "CMS Update: Content changes"], cwd=ROOT_DIR, check=False, capture_output=True, text=True)
        
        if commit_proc.returncode != 0:
            if "nothing to commit" in commit_proc.stdout or "nothing to commit" in commit_proc.stderr:
                pass
            else:
                commit_proc.check_returncode()
        
        # Push (credentials are now in the remote URL if retrieval worked)
        subprocess.run(["git", "push"], cwd=ROOT_DIR, check=True, capture_output=True)
        return True, "Successfully pushed to GitHub!"
    except subprocess.CalledProcessError as e:
        # Return the stderr from the failed command
        error_msg = e.stderr.decode().strip() if e.stderr else str(e)
        return False, f"Git Error: {error_msg}"
    except Exception as e:
        return False, str(e)

def run_search_index():
    try:
        # Now this script rebuilds articles.html and search.json
        # Use sys.executable to ensure we use the same python env
        result = subprocess.run(
            [sys.executable, "generate_search_index.py"], 
            cwd=ROOT_DIR, 
            capture_output=True, 
            text=True, 
            check=True
        )
        return True, "Site Rebuilt: Search Index and Article Listings Updated!"
    except subprocess.CalledProcessError as e:
        return False, f"Error running output script: {e.stderr}"
    except Exception as e:
        return False, str(e)

def backup_drafts():
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    backup_dir = os.path.join(BACKEND_DIR, "backups")
    os.makedirs(backup_dir, exist_ok=True)
    archive_name = os.path.join(backup_dir, f"drafts_backup_{timestamp}")
    try:
        shutil.make_archive(archive_name, 'zip', PATHS["draft_articles"])
        shutil.make_archive(archive_name + "_projects", 'zip', PATHS["draft_projects"])
        return True, f"Backup created: {os.path.basename(archive_name)}.zip"
    except Exception as e:
        return False, str(e)

# --- NEW HELPERS (BULK & PROJECTS) ---

def toggle_project_card(file_path, card_title, hide=True):
    with open(file_path, 'r', encoding='utf-8') as f:
        soup = BeautifulSoup(f, 'html.parser')
    
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
            target_path = None
            if a_tag and a_tag.get('href') and a_tag.get('href').startswith('../'):
                clean_rel = a_tag.get('href').replace('../', '')
                pot_path = os.path.join(ROOT_DIR, clean_rel)
                target_path = pot_path
            
            project_list.append({
                "title": title,
                "hidden": is_hidden,
                "target": target_path
            })
    return project_list

def manage_project_item(ml_page, title, target_file, action):
    # 1. Update Card Type
    hide_card = (action != 'public')
    toggle_project_card(ml_page, title, hide=hide_card)
    
    # 2. Update File
    if not target_file: return
    fname = os.path.basename(target_file)
    draft_path = os.path.join(PATHS["draft_articles"], fname)
    public_path = target_file
    
    real_path = public_path
    if not os.path.exists(public_path) and os.path.exists(draft_path):
        real_path = draft_path
    
    if os.path.exists(real_path):
        set_visibility(real_path, action)

def update_homepage_listings():
    """
    Refreshes the 'Latest Articles' list in index.html
    """
    import random
    
    # 1. Gather Articles
    files = get_files(PATHS["public_articles"])
    articles = []
    
    for p in files:
        if "template.html" in p: continue
        
        with open(p, 'r', errors='ignore') as f:
            soup = BeautifulSoup(f, 'html.parser')
            
        # Skip Unlisted
        meta_vis = soup.find('meta', attrs={'name': 'visibility'})
        if meta_vis and meta_vis.get('content') == 'unlisted':
            continue
            
        title = soup.title.string.split('|')[0].strip() if soup.title else "Untitled"
        
        # Date
        date_str = ""
        date_obj = datetime.datetime.min
        meta_date = soup.find(class_='article-meta-small')
        if meta_date:
            txt = meta_date.get_text().strip().split('•')[0].strip()
            date_str = txt
            try:
                date_obj = datetime.datetime.strptime(txt, "%b %d, %Y")
            except:
                pass
                
        # Link
        link = f"articles/{os.path.basename(p)}"
        
        articles.append({
            "title": title,
            "date": date_str,
            "dt": date_obj,
            "link": link
        })
        
    # 2. Sort & Pick Top 3
    articles.sort(key=lambda x: x['dt'], reverse=True)
    top_3 = articles[:3]
    
    # 3. Generate HTML
    new_cards_html = ""
    gradients = [
        "linear-gradient(135deg, #2563EB, #1E40AF)",
        "linear-gradient(135deg, #10B981, #059669)",
        "linear-gradient(135deg, #8B5CF6, #6D28D9)", 
        "linear-gradient(135deg, #F59E0B, #D97706)",
        "linear-gradient(135deg, #EC4899, #DB2777)"
    ]
    
    for i, art in enumerate(top_3):
        grad = gradients[i % len(gradients)]
        card = f"""
        <article class="article-card">
            <div class="article-card-image">
                <div class="placeholder-img" style="background: {grad};"></div>
                <div class="blog-overlay"><i class="fas fa-robot"></i></div>
            </div>
            <div class="article-card-content">
                <span class="article-meta-small">{art['date']}</span>
                <h3>{art['title']}</h3>
                <a href="{art['link']}" class="article-read-btn">Read Article</a>
            </div>
        </article>
        """
        new_cards_html += card

    # 4. Update index.html
    with open(PATHS["index"], 'r', encoding='utf-8') as f:
        main_soup = BeautifulSoup(f, 'html.parser')
        
    grid = main_soup.find('div', class_='articles-grid')
    if grid:
        grid.clear()
        # Parse new HTML and append
        # BeautifulSoup parsing of fragment
        frag = BeautifulSoup(new_cards_html, 'html.parser')
        grid.append(frag)
        
        with open(PATHS["index"], 'w', encoding='utf-8') as f:
            f.write(str(main_soup))
            
    return True

def render_bulk_actions(selection_key, item_type="files", custom_handler=None, key_suffix=""):
    """
    Renders Vertical Action Buttons (Toolbar style) using session state
    """
    selected_items = st.session_state.get(selection_key, set())
    
    if not selected_items:
        st.info("👈 Select items to see actions")
        return

    st.markdown("#### Bulk Actions")
    st.caption(f"Selected: {len(selected_items)} items")
    
    def process_bulk(action):
        count = 0
        with st.spinner(f"Processing {len(selected_items)} items..."):
            for item in selected_items:
                if custom_handler:
                    custom_handler(item, action)
                else:
                    set_visibility(item, action)
                count += 1
            
            # --- AUTO UPDATE TRIGGER ---
            st.toast("Regenerating site listings...", icon="🔄")
            ok, msg = run_search_index()
            if ok:
                st.toast(msg, icon="✅")
            else:
                st.error(f"Site rebuild failed: {msg}")
        
        # Clear selection after action
        st.session_state[selection_key] = set()
        st.success(f"Updated {count} {item_type} to '{action}' and rebuilt site!")
        st.rerun()

    # Vertical Stack of Buttons
    if st.button(f"Make Public 🟢", key=f"bulk_pub_{key_suffix}", use_container_width=True):
        process_bulk('public')
    
    if st.button(f"Make Unlisted 🟡", key=f"bulk_unl_{key_suffix}", use_container_width=True):
        process_bulk('unlisted')
    
    if st.button(f"Move to Drafts 🔴", key=f"bulk_drf_{key_suffix}", use_container_width=True):
        process_bulk('private')

def render_file_list(files, selection_key, all_items=None, key_suffix=""):
    """
    Renders file list with persistent selection state.
    all_items: Optional, list of all available items (unfiltered) to allow global selection.
    Returns: None (Uses st.session_state[selection_key])
    """
    # Initialize session state for this selection group if not exists
    if selection_key not in st.session_state:
        st.session_state[selection_key] = set()

    # Helpers to manage selection
    def toggle_item(item_id):
        if item_id in st.session_state[selection_key]:
            st.session_state[selection_key].remove(item_id)
        else:
            st.session_state[selection_key].add(item_id)
            
    def select_list(items_to_select):
        for p in items_to_select:
             # handle complex objects if files contains dicts (Projects ML items)
             val = p if isinstance(p, str) else p['title']
             st.session_state[selection_key].add(val)
             
             # Sync widget state
             if isinstance(p, str):
                 name = os.path.basename(p)
             else:
                 name = p['title']
             widget_key = f"chk_{key_suffix}_{name}"
             
             # Only update widget key if it exists/we are going to render it?
             # Actually, if we select GLOBAL, we might select items NOT visible.
             # We should only update the widget key if we think Streamlit needs it.
             # Setting it safely doesn't hurt.
             st.session_state[widget_key] = True
        st.rerun()

    def select_all_visible():
        select_list(files)
        
    def select_global():
        if all_items:
            select_list(all_items)

    def deselect_all_visible():
        for p in files:
             val = p if isinstance(p, str) else p['title']
             if val in st.session_state[selection_key]:
                 st.session_state[selection_key].remove(val)
             
             # Sync widget state
             if isinstance(p, str):
                 name = os.path.basename(p)
             else:
                 name = p['title']
             widget_key = f"chk_{key_suffix}_{name}"
             st.session_state[widget_key] = False
        st.rerun()

    # Bulk Controls
    # Layout: [Select Visible] [Deselect Visible] ... [Select Global (if filtered)]
    cols = st.columns(3 if (all_items and len(files) < len(all_items)) else 2)
    
    with cols[0]:
        if st.button("Select All Visible", key=f"sel_all_{key_suffix}", use_container_width=True):
            select_all_visible()
    with cols[1]:
        if st.button("Deselect Visible", key=f"desel_all_{key_suffix}", use_container_width=True):
            deselect_all_visible()
            
    if all_items and len(files) < len(all_items):
         with cols[2]:
             if st.button(f"Select Entire Library ({len(all_items)})", key=f"sel_glob_{key_suffix}", use_container_width=True):
                 select_global()

    # Render List
    for p in files:
        if isinstance(p, str) and "template.html" in p: continue
        
        # Determine Value and Display String
        if isinstance(p, str):
            value = p
            name = os.path.basename(p)
            status_icon = "🟢"
            if "drafts" in p: 
                status_icon = "🔴"
            else:
                with open(p, 'r', errors='ignore') as f:
                    if 'content="unlisted"' in f.read():
                        status_icon = "🟡"
        else:
            # Complex object (e.g., from project cards)
            value = p['title']
            name = p['title']
            
            # Reconstruct status logic from the dict
            is_hidden = p.get('hidden', False)
            status_icon = "🔴" if is_hidden else "🟢"
            target = p.get('target')
            if target and os.path.exists(target):
                 with open(target, 'r', errors='ignore') as f:
                    if 'content="unlisted"' in f.read():
                        status_icon = "🟡"

        # Check interaction
        is_selected = value in st.session_state[selection_key]
        
        # Uniquely identify the checkbox
        col1, col2 = st.columns([0.1, 1])
        with col1:
             # We use the callback to toggle state
             if st.checkbox("", value=is_selected, key=f"chk_{key_suffix}_{name}", on_change=toggle_item, args=(value,)):
                 pass # Logic handled in on_change
        with col2:
            st.write(f"{status_icon} {name}")

# --- UI ---

st.title("⚡ AI Portfolio Dashboard")

# DEBUG INFO (Collapsed)
with st.expander("Debug: Check Paths"):
    st.write(f"**Root Dir:** `{ROOT_DIR}`")
    st.write(f"**Files Found:** {len(get_files(PATHS['public_articles']))}")

tabs = st.tabs(["📄 Articles", "🚀 Projects", "🎨 Sections & Menu", "📝 New Content", "⚙️ Deploy & Backup"])

# --- TAB 1: ARTICLES ---
with tabs[0]:
    st.header("Manage Articles")
    
    # Left: List | Right: Controls
    
    # 1. Split Public vs Unlisted
    all_public_raw = get_files(PATHS["public_articles"])
    real_public = []
    unlisted_articles = []
    
    for p in all_public_raw:
        is_unlisted = False
        try:
            with open(p, 'r', errors='ignore') as f:
                if 'content="unlisted"' in f.read():
                    is_unlisted = True
        except:
            pass
            
        if is_unlisted:
            unlisted_articles.append(p)
        else:
            real_public.append(p)

    # --- Section 1: Public Articles ---
    c_head, c_search = st.columns([2, 1])
    with c_head:
         st.subheader("🟢 Public Articles")
    with c_search:
         search_pub = st.text_input("Search", key="s_pub", placeholder="🔍 Filter public...", label_visibility="collapsed")

    c1, c2 = st.columns([3, 1])
    with c1:
        display_public = real_public
        if search_pub:
            display_public = [f for f in display_public if search_pub.lower() in os.path.basename(f).lower()]
            
        with st.container(height=400, border=True):
             render_file_list(display_public, "selected_pub_articles", all_items=real_public, key_suffix="art_pub")
    with c2:
        render_bulk_actions("selected_pub_articles", "articles", key_suffix="art_pub_act")

    st.divider()

    # --- Section 2: Unlisted Articles ---
    st.subheader("🟡 Unlisted Articles")
    c_unl_1, c_unl_2 = st.columns([3, 1])
    with c_unl_1:
         with st.container(height=250, border=True):
             render_file_list(unlisted_articles, "selected_unlisted_articles", key_suffix="art_unl")
    with c_unl_2:
         render_bulk_actions("selected_unlisted_articles", "articles", key_suffix="art_unl_act")

    st.divider()

    # 2. Drafts
    c_head_draft, c_search_draft = st.columns([2, 1])
    with c_head_draft:
        st.subheader("🔴 Drafts")
    with c_search_draft:
        search_draft = st.text_input("Search", key="s_draft", placeholder="🔍 Filter drafts...", label_visibility="collapsed")

    c3, c4 = st.columns([3, 1])
    
    with c3:
        draft_all = get_files(PATHS["draft_articles"])
        draft_files = draft_all
        
        if search_draft:
            draft_files = [f for f in draft_files if search_draft.lower() in os.path.basename(f).lower()]
            
        with st.container(height=300, border=True):
            render_file_list(draft_files, "selected_draft_articles", all_items=draft_all, key_suffix="art_draft")
    with c4:
        render_bulk_actions("selected_draft_articles", "drafts", key_suffix="art_draft_act")

# --- TAB 2: PROJECTS ---
with tabs[1]:
    st.header("Manage Projects")
    
    # 1. Project Pages (Split Public vs Unlisted)
    all_proj_raw = get_files(PATHS["public_projects"])
    real_proj = []
    unlisted_proj = []
    
    for p in all_proj_raw:
        is_unlisted = False
        try:
             with open(p, 'r', errors='ignore') as f:
                    if 'content="unlisted"' in f.read():
                        is_unlisted = True
        except: pass
        
        if is_unlisted:
            unlisted_proj.append(p)
        else:
            real_proj.append(p)

    # Public Projects
    st.subheader("📂 Public Project Pages")
    c1, c2 = st.columns([3, 1])
    
    with c1:
        with st.container(height=300, border=True):
            render_file_list(real_proj, "selected_projects", key_suffix="proj_main")
    with c2:
        render_bulk_actions("selected_projects", "projects", key_suffix="proj_main_act")

    st.divider()

    # Unlisted Projects
    st.subheader("🟡 Unlisted Project Pages")
    c_u1, c_u2 = st.columns([3, 1])
    with c_u1:
         with st.container(height=200, border=True):
             render_file_list(unlisted_proj, "selected_unlisted_projects", key_suffix="proj_unl")
    with c_u2:
         render_bulk_actions("selected_unlisted_projects", "projects", key_suffix="proj_unl_act")

    st.divider()

    # 2. Draft Projects
    st.subheader("📂 Draft Project Pages")
    c3, c4 = st.columns([3, 1])
    
    with c3:
        draft_proj_files = get_files(PATHS["draft_projects"])
        with st.container(height=300, border=True):
            render_file_list(draft_proj_files, "selected_draft_projects", key_suffix="proj_draft")
    with c4:
        render_bulk_actions("selected_draft_projects", "projects", key_suffix="proj_draft_act")

    st.divider()

    # 2. Specific Items
    c_head2, c_search2 = st.columns([2, 1])
    with c_head2:
        st.subheader("🧩 Machine Learning Items")
    with c_search2:
        search_ml = st.text_input("Search", key="s_ml", placeholder="🔍 Filter items...", label_visibility="collapsed")

    ml_page = os.path.join(PATHS["public_projects"], "machine_learning.html")
    
    if os.path.exists(ml_page):
        cards = get_project_cards(ml_page)
        
        # Filter Cards
        if search_ml:
            cards = [c for c in cards if search_ml.lower() in c['title'].lower()]
        
        c3, c4 = st.columns([3, 1])
        
        with c3:
            if not cards:
                st.info("No items found.")
            
            with st.container(height=500, border=True):
                # We need to map cards back to the objects needed by render_file_list
                # Actually render_file_list now handles dicts, so we pass cards directly
                render_file_list(cards, "selected_ml_items", key_suffix="ml_items")
        
        with c4:
            # We need to reconstruct the objects for the handler from the keys (titles)
            # The bulk action generic handler passes the *item* from the set
            # But our set now stores TITLES for cards.
            # So we need a wrapper to find the full object if needed, OR just pass title if that's enough.
            # manage_project_item needs: ml_page, title, target_file, action
            # To get target_file, we need to look it up from the title.
            
            # Let's rebuild the map for quick lookup
            title_to_card_map = {c['title']: c for c in get_project_cards(ml_page)} # Re-read full list for lookup
            
            def ml_handler(item_title, action):
                card_data = title_to_card_map.get(item_title)
                if card_data:
                    manage_project_item(ml_page, card_data['title'], card_data['target'], action)
                
            render_bulk_actions("selected_ml_items", "ML Items", custom_handler=ml_handler, key_suffix="ml_act")
            
    else:
        st.warning("machine_learning.html not found")

# --- TAB 3: SECTIONS ---
with tabs[2]:
    st.header("Homepage Sections")
    
    with open(PATHS["index"], 'r') as f:
        index_html = f.read()
    
    sections = {
        "projects": "Guided Projects Section",
        "articles": "Latest Articles Section",
        "courses": "Recommended Resources"
    }
    
    for sec_id, label in sections.items():
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
    st.header("📝 Write New Article")
    
    # Initialize session state for content if not exists
    if 'editor_content' not in st.session_state:
        st.session_state.editor_content = ""
    
    # 1. Metadata
    with st.expander("Article Metadata", expanded=True):
        c1, c2 = st.columns([3, 1])
        with c1:
            new_title = st.text_input("Title", placeholder="e.g., 10 AI Projects for 2026")
        with c2:
            new_date = st.date_input("Date", datetime.date.today())
        new_desc = st.text_area("Description (SEO)", height=70, placeholder="Brief summary for search engines and cards...")

    # 2. Asset Uploader
    with st.expander("📂 Upload Images & Files"):
        uploaded_file = st.file_uploader("Choose an image...", type=['png', 'jpg', 'jpeg', 'gif', 'svg'])
        
        if uploaded_file is not None:
             # Ensure directory exists
             upload_dir = os.path.join(ROOT_DIR, "assets", "uploads")
             os.makedirs(upload_dir, exist_ok=True)
             
             # Save file
             file_path = os.path.join(upload_dir, uploaded_file.name)
             with open(file_path, "wb") as f:
                 f.write(uploaded_file.getbuffer())
             
             # Show snippet
             rel_path = f"assets/uploads/{uploaded_file.name}" # simplified path
             snippet = f"![Image Descriptions](../{rel_path})"
             st.success(f"Saved!")
             st.code(snippet, language="markdown")
             st.caption("Copy the snippet above and paste it into the editor.")

    # 3. Editor Toolbar helpers
    def add_text(text):
        st.session_state.editor_content += text

    # 4. Main Editor Interface
    st.subheader("Content Editor")
    
    # Toolbar
    tb1, tb2, tb3, tb4, tb5, tb6, tb7 = st.columns([1, 1, 1, 1, 1, 1, 6])
    with tb1: 
        if st.button("Bd", help="Bold"): add_text("**bold text**")
    with tb2: 
        if st.button("It", help="Italic"): add_text("*italic text*")
    with tb3: 
        if st.button("Cd", help="Code"): add_text("`code`")
    with tb4: 
        if st.button("Lk", help="Link"): add_text("[Link Text](url)")
    with tb5: 
        if st.button("Img", help="Image"): add_text("![Alt Text](image_url)")
    with tb6:
        if st.button("Blk", help="Code Block"): add_text("\n```python\nprint('Hello')\n```\n")

    # Split View
    c_edit, c_view = st.columns(2)
    
    with c_edit:
        st.caption("Markdown Input")
        # Text Area bound to session state
        content_input = st.text_area(
            "Type here...", 
            value=st.session_state.editor_content, 
            height=600, 
            label_visibility="collapsed",
            key="editor_key"
        )
        # Sync back to session state logic (if user typed manually)
        st.session_state.editor_content = content_input

    with c_view:
        st.caption("Live Preview")
        with st.container(height=600, border=True):
            if st.session_state.editor_content:
                st.markdown(st.session_state.editor_content)
            else:
                st.info("Preview will appear here...")

    # 5. Create Action
    st.divider()
    if st.button("Create Draft Article 🚀", type="primary", use_container_width=True):
        if new_title and st.session_state.editor_content:
            try:
                import markdown
                # Basic Extensions for better rendering transparency
                html_content = markdown.markdown(st.session_state.editor_content, extensions=['fenced_code', 'tables'])
            except:
                html_content = f"<p>{st.session_state.editor_content}</p>"
            
            save_path = create_article(new_title, new_desc, new_date.strftime("%b %d, %Y"), html_content)
            st.success(f"Draft created successfully at: `{save_path}`")
            st.balloons()
        else:
            st.error("Please provide at least a Title and Content.")

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
