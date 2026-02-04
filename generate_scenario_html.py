import os
import re
import json

# Configuration
BASE_DIR = "/Users/air/Documents/Air Date/TRPG/できらぁの会/28時の深夜ラジオ"
OUTPUT_FILE = os.path.join(BASE_DIR, "28時の深夜ラジオ_session.html")
TEMPLATE_FILE = os.path.join(BASE_DIR, "990_管理メモ/ideal_template.html")
EXCLUDE_DIRS = ["990_管理メモ", "scripts", "素材", ".git", ".idea", "Newテンプレ", "サンプル", "Newテンプレート"]
EXCLUDE_FILES = [
    ".DS_Store", 
    "28時の深夜ラジオ_session.html", 
    "generate_scenario_html.py", 
    "ideal_template.html", 
    "scenario_template.html",
    "案（アイディアまとめ）.txt",
    "概要.txt"
]

def load_template(path):
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()

def escape_html(text):
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")

def parse_text_to_html(text, filename):
    lines = text.split('\n')
    html_parts = []
    
    in_script_box = False
    pending_script_line = None # {name, text}

    def flush_script_line():
        nonlocal pending_script_line
        if pending_script_line:
            html_parts.append(f'''
                <div class="script-line">
                    <span class="script-name">{pending_script_line['name']}</span>
                    <span class="script-text">{pending_script_line['text']}</span>
                </div>''')
            pending_script_line = None

    # Special handling for Zero Signal Paradox
    if filename == "シナリオ_ゼロ・シグナル・パラドクス.txt":
        html_parts.append('''
        <div class="card" style="border-left: 4px solid var(--warning); background: rgba(251, 191, 36, 0.1);">
            <h3>⚠️ AI生成原案</h3>
            <p>このファイルは、AIが最初に提案した原案となるシナリオです。現在の決定稿とは内容が異なる可能性があります。</p>
        </div>
        ''')

    i = 0
    while i < len(lines):
        line = lines[i].rstrip()
        
        # RAW HTML BLOCK CHECK: {{{
        if line.strip() == '{{{':
            flush_script_line()
            if in_script_box:
                html_parts.append('</div>')
                in_script_box = False
            
            raw_html = []
            i += 1
            while i < len(lines):
                if lines[i].strip() == '}}}':
                    break
                raw_html.append(lines[i])
                i += 1
            html_parts.append('\n'.join(raw_html))
            i += 1
            continue

        # Empty line
        if not line:
            # If we have a pending script line, it might be a pause or end of speech.
            # But usually empty lines are just spacing.
            # If we are in script box, we keep it open unless we hit non-dialogue.
            # But we should flush the current line.
            flush_script_line()
            i += 1
            continue

        # Header check (■ or 【)
        if line.startswith('■') or line.startswith('【'):
            flush_script_line()
            if in_script_box:
                html_parts.append('</div>')
                in_script_box = False
            header_text = escape_html(line.strip('■【】 '))
            html_parts.append(f'<h3>{header_text}</h3>')
            i += 1
            continue

        # Dialogue check (Name: "Text" or Name: Text or Name：「Text」)
        dialogue_match = re.match(r'^([^\s「：]+)[：:](.+)$', line)
        if dialogue_match:
            flush_script_line()
            
            name = escape_html(dialogue_match.group(1).strip())
            content = escape_html(dialogue_match.group(2).strip())
            
            if not in_script_box:
                html_parts.append('<div class="script-box">')
                in_script_box = True
            
            pending_script_line = {'name': name, 'text': content}
            i += 1
            continue
        
        # Continuation check
        if in_script_box:
            # Check for explicitly non-dialogue things (Notes)
            if line.startswith('（') or line.startswith('('):
                flush_script_line()
                html_parts.append('</div>') # Close box to insert note
                in_script_box = False
                note_text = escape_html(line)
                html_parts.append(f'<p class="note" style="color:var(--text-secondary); font-style:italic;">{note_text}</p>')
                i += 1
                continue
                
            # Check if it looks like a continuation
            if pending_script_line and (line.startswith(' ') or line.startswith('　') or not re.match(r'^[^\s]+$', line)):
                pending_script_line['text'] += "<br>" + escape_html(line.strip())
                i += 1
                continue
            elif not pending_script_line and (line.startswith(' ') or line.startswith('　')):
                 pass
            
            # If none of above, treat as normal paragraph, close box
            flush_script_line()
            html_parts.append('</div>')
            in_script_box = False
            p_text = escape_html(line)
            html_parts.append(f'<p>{p_text}</p>')
            i += 1
            continue

        # Normal text (outside box)
        if line.startswith('（') or line.startswith('('):
            note_text = escape_html(line)
            html_parts.append(f'<p class="note" style="color:var(--text-secondary); font-style:italic;">{note_text}</p>')
        else:
            p_text = escape_html(line)
            html_parts.append(f'<p>{p_text}</p>')
        
        i += 1

    flush_script_line()
    if in_script_box:
        html_parts.append('</div>')
        
    return '\n'.join(html_parts)

def build_tree_and_content(current_dir, depth=0):
    items = []
    content_htmls = []
    
    try:
        entries = sorted(os.listdir(current_dir))
    except OSError:
        return "", ""

    # Sort entries: directories first, then files? Or alphanumeric?
    # Usually consistent alphanumeric is best for TRPG scenario flow if numbered (00_, 01_)
    entries.sort()

    for entry in entries:
        full_path = os.path.join(current_dir, entry)
        
        if entry in EXCLUDE_FILES:
            continue
        if entry.startswith('.'):
            continue

        if os.path.isdir(full_path):
            if entry in EXCLUDE_DIRS:
                continue
            
            # Directory
            # Generate ID for folder
            folder_id = f"dir_{abs(hash(full_path))}" 
            child_items, child_contents = build_tree_and_content(full_path, depth + 1)
            
            if child_items: # Only show folder if it has content
                items.append(f'''
                <div class="tree-item has-children expanded">
                    <div class="tree-label" style="--depth: {depth}" onclick="toggleFolder(this)">
                        <span class="tree-arrow">▶</span>
                        <div style="display:flex; align-items:center; gap:4px;">
                            <input type="checkbox" class="progress-checkbox" data-id="{folder_id}" onclick="event.stopPropagation(); toggleCheck(this)">
                            <span class="tree-icon">📂</span>
                        </div>
                        <span>{escape_html(entry)}</span>
                    </div>
                    <div class="tree-children">
                        {child_items}
                    </div>
                </div>
                ''')
                content_htmls.append(child_contents)
                
        else:
            # File
            if not entry.endswith('.txt'):
                continue
                
            file_id = f"file_{abs(hash(full_path))}"
            
            # Sidebar Item
            items.append(f'''
            <div class="tree-item" onclick="openPage('{file_id}', this)">
                <div class="tree-label" style="--depth: {depth}">
                    <span class="tree-arrow"></span>
                    <div style="display:flex; align-items:center; gap:4px;">
                        <input type="checkbox" class="progress-checkbox" data-id="{file_id}" onclick="event.stopPropagation(); toggleCheck(this)">
                        <span class="tree-icon">📄</span>
                    </div>
                    <span>{escape_html(entry)}</span>
                </div>
            </div>
            ''')
            
            # Content Page
            with open(full_path, 'r', encoding='utf-8') as f:
                raw_text = f.read()
            
            html_body = parse_text_to_html(raw_text, entry)
            
            content_htmls.append(f'''
            <div id="{file_id}" class="page" data-filename="{escape_html(entry)}">
                <h2>{escape_html(entry)}</h2>
                <div class="page-content">
                    {html_body}
                </div>
            </div>
            ''')

    return '\n'.join(items), '\n'.join(content_htmls)

def inject_extra_js():
    return """
    <script>
    // --- Dynamic Highlighting & Checkbox Logic ---

    // Checkbox Logic
    function toggleCheck(checkbox) {
        // Save state
        saveProgress();
    }

    function saveProgress() {
        const checkedIds = [];
        document.querySelectorAll('.progress-checkbox:checked').forEach(cb => {
            checkedIds.push(cb.getAttribute('data-id'));
        });
        localStorage.setItem('scenario_progress_' + document.title, JSON.stringify(checkedIds));
    }

    function loadProgress() {
        const saved = JSON.parse(localStorage.getItem('scenario_progress_' + document.title) || '[]');
        saved.forEach(id => {
            const cb = document.querySelector(`.progress-checkbox[data-id="${id}"]`);
            if (cb) cb.checked = true;
        });
    }

    // Highlighting Logic
    const highlightRules = [
        { keywords: ['SAN', '正気度', '1d', '1D'], className: 'highlight-san', style: 'background:#ffebee; color:#c62828; padding:2px 4px; border-radius:3px;' },
        { keywords: ['目星', '聞き耳', '図書館', '判定', '成功', '失敗'], className: 'highlight-skill', style: 'background:#e3f2fd; color:#1565c0; padding:2px 4px; border-radius:3px;' },
        { keywords: ['NPC', '？？？'], className: 'highlight-npc', style: 'background:#fff9c4; color:#f57f17; padding:2px 4px; border-radius:3px;' }
    ];

    function applyHighlights() {
        // Only run on visible page to save perf? Or run on all? 
        // Let's run on standard text nodes in paragraphs and spans
        const contentArea = document.querySelector('.content-area');
        if(!contentArea) return;
        
        // Use TreeWalker for efficient text node traversal
        const walker = document.createTreeWalker(contentArea, NodeFilter.SHOW_TEXT, null, false);
        let node;
        const nodesToReplace = [];

        while(node = walker.nextNode()) {
            // Skip inside script tags or already highlighted tags
            if (node.parentElement.tagName === 'SCRIPT' || 
                node.parentElement.tagName === 'STYLE' ||
                node.parentElement.classList.contains('highlight-san') ||
                node.parentElement.classList.contains('highlight-skill') ||
                node.parentElement.classList.contains('highlight-npc')) {
                continue;
            }

            let text = node.nodeValue;
            let modified = false;
            let newHtml = text.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");

            highlightRules.forEach(rule => {
                 rule.keywords.forEach(kw => {
                    // Simple replacement, might break if keywords overlap (e.g., "SAN" and "SAN Check")
                    // For now, simple approach is fine
                    const regex = new RegExp(`(${kw})`, 'gi');
                    if (regex.test(newHtml)) {
                        newHtml = newHtml.replace(regex, `<span class="${rule.className}" style="${rule.style}">$1</span>`);
                        modified = true;
                    }
                 });
            });

            if (modified) {
                const span = document.createElement('span');
                span.innerHTML = newHtml;
                nodesToReplace.push({ oldNode: node, newNode: span });
            }
        }

        nodesToReplace.forEach(item => {
            item.oldNode.parentElement.replaceChild(item.newNode, item.oldNode);
        });
    }

    // Initialize
    window.addEventListener('DOMContentLoaded', () => {
        loadProgress();
        // applyHighlights(); // Call this immediately or maybe on page switch?
        // Better to apply once or lazily. Let's apply once for now as the content is static in DOM.
        applyHighlights();
    });

    </script>
    """

def main():
    print("Loading template...")
    template = load_template(TEMPLATE_FILE)
    
    print("Building tree...")
    sidebar_html, content_html = build_tree_and_content(BASE_DIR)
    
    print("Injecting content...")
    # Replace sidebar placeholder
    # Ideal template has: <!-- Tree content --> ... <!-- Root Files -->
    # We will replace the whole inner content of #file-tree for simplicity or find the marker
    
    if '<!-- Tree content -->' in template:
        # Simple split replace
        parts = template.split('<!-- Tree content -->')
        # We assume the template structure is roughly: Header... Sidebar... <!-- Tree content --> ... default items ... </aside>
        # We want to keep the sidebar-header but replace the list.
        # However, the template has some hardcoded "Root Files" after the marker.
        # We should probably replace everything inside <div class="sidebar-content" id="file-tree">
        
        # Regex to find the div content
        output_html = re.sub(
            r'(<div class="sidebar-content" id="file-tree">).*?(</div>\s*</aside>)', 
            r'\1' + '\n' + sidebar_html + '\n' + r'\2', 
            template, 
            flags=re.DOTALL
        )
    else:
        # Fallback
        output_html = template.replace('</body>', f'<div style="color:red">Error: Template structure changed</div></body>')

    # Replace content area
    # Template has: <div class="content-area"> ... default pages ... </div>
    # We want to clear default pages and insert ours
    output_html = re.sub(
        r'(<div class="content-area">).*?(</div>\s*</main>)', 
        r'\1' + '\n' + content_html + '\n' + r'\2', 
        output_html, 
        flags=re.DOTALL
    )

    # Inject Extra JS before body end
    output_html = output_html.replace('</body>', inject_extra_js() + '\n</body>')

    # Update title
    output_html = output_html.replace('<span id="scenario-title">シナリオ名（テンプレート）</span>', '<span id="scenario-title">28時の深夜ラジオ</span>')

    print(f"Writing to {OUTPUT_FILE}...")
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write(output_html)
    
    print("Done!")

if __name__ == "__main__":
    main()
