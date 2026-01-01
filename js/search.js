document.addEventListener('DOMContentLoaded', () => {
    const searchTrigger = document.getElementById('search-trigger');
    const searchOverlay = document.getElementById('search-overlay');
    const searchClose = document.getElementById('search-close');
    const searchInput = document.getElementById('search-input');
    const searchResults = document.getElementById('search-results');

    let searchIndex = [];

    // Determine base path based on current location (root vs subpages)
    // Checks if we are in 'articles' or 'projects' directories
    const isSubPage = window.location.pathname.includes('/articles/') ||
        window.location.pathname.includes('/projects/');
    const basePath = isSubPage ? '../' : '';

    // Fetch Search Index
    fetch(`${basePath}search.json`)
        .then(response => response.json())
        .then(data => {
            searchIndex = data;
        })
        .catch(error => console.error('Error loading search index:', error));

    // Open Search Overlay
    if (searchTrigger) {
        searchTrigger.addEventListener('click', () => {
            searchOverlay.classList.add('active');
            searchInput.focus();
        });
    }

    // Close Search Overlay
    if (searchClose) {
        searchClose.addEventListener('click', () => {
            searchOverlay.classList.remove('active');
            searchInput.value = '';
            searchResults.innerHTML = '';
        });
    }

    // Close on Escape key
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && searchOverlay.classList.contains('active')) {
            searchOverlay.classList.remove('active');
        }
    });

    // Search Logic
    if (searchInput) {
        searchInput.addEventListener('input', (e) => {
            const query = e.target.value.toLowerCase();
            searchResults.innerHTML = '';

            if (query.length < 2) return;

            const results = searchIndex.filter(item => {
                const titleMatch = item.title.toLowerCase().includes(query);
                const descMatch = item.description.toLowerCase().includes(query);
                return titleMatch || descMatch;
            });

            if (results.length > 0) {
                results.forEach(item => {
                    const li = document.createElement('div');
                    li.className = 'search-result-item';

                    // Image Handling
                    let imageHtml = '';
                    if (item.image) {
                        // Fix image path relative to current page
                        // item.image is like "assets/..."
                        const imgPath = item.image.startsWith('http') ? item.image : basePath + item.image;
                        imageHtml = `<div class="search-result-image"><img src="${imgPath}" alt="${item.title}" loading="lazy"></div>`;
                    } else {
                        // Default icon based on category
                        let icon = 'fa-file-alt';
                        if (item.category === 'Project') icon = 'fa-code-branch';
                        imageHtml = `<div class="search-result-icon"><i class="fas ${icon}"></i></div>`;
                    }

                    // Fix link URL relative to current page
                    // item.url is like "articles/..." or "about.html"
                    const linkUrl = item.url.startsWith('http') ? item.url : basePath + item.url;

                    li.innerHTML = `
                        <a href="${linkUrl}" class="search-result-link">
                            ${imageHtml}
                            <div class="search-result-content">
                                <h4>${item.title}</h4>
                                <p>${item.description}</p>
                                <div class="search-meta">
                                    <span class="search-category">${item.category}</span>
                                    ${item.date ? `<span class="search-date">${item.date}</span>` : ''}
                                </div>
                            </div>
                        </a>
                    `;
                    searchResults.appendChild(li);
                });
            } else {
                searchResults.innerHTML = '<div class="no-results">No results found</div>';
            }
        });
    }
});
