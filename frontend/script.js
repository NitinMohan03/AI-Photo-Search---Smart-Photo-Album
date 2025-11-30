// Global state
let selectedFiles = [];

// DOM Elements
const dragDropZone = document.getElementById('dragDropZone');
const fileInput = document.getElementById('fileInput');
const customLabelsInput = document.getElementById('customLabels');
const uploadButton = document.getElementById('uploadButton');
const searchInput = document.getElementById('searchInput');
const searchButton = document.getElementById('searchButton');
const selectedFilesContainer = document.getElementById('selectedFiles');
const uploadProgressContainer = document.getElementById('uploadProgress');
const resultsContainer = document.getElementById('resultsContainer');

// Initialize event listeners
function init() {
    // Drag and drop listeners
    dragDropZone.addEventListener('click', () => fileInput.click());
    dragDropZone.addEventListener('dragover', handleDragOver);
    dragDropZone.addEventListener('dragleave', handleDragLeave);
    dragDropZone.addEventListener('drop', handleDrop);

    // File input listener
    fileInput.addEventListener('change', handleFileSelect);

    // Upload button listener
    uploadButton.addEventListener('click', handleUpload);

    // Search listeners
    searchButton.addEventListener('click', handleSearch);
    searchInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') handleSearch();
    });
}

// Drag and drop handlers
function handleDragOver(e) {
    e.preventDefault();
    dragDropZone.classList.add('drag-over');
}

function handleDragLeave(e) {
    e.preventDefault();
    dragDropZone.classList.remove('drag-over');
}

function handleDrop(e) {
    e.preventDefault();
    dragDropZone.classList.remove('drag-over');

    const files = Array.from(e.dataTransfer.files);
    addFiles(files);
}

function handleFileSelect(e) {
    const files = Array.from(e.target.files);
    addFiles(files);
}

// Add files to selection
function addFiles(files) {
    const validFiles = files.filter(file => {
        const validTypes = ['image/png', 'image/jpg', 'image/jpeg'];
        return validTypes.includes(file.type);
    });

    selectedFiles = [...selectedFiles, ...validFiles];
    renderSelectedFiles();
    uploadButton.disabled = selectedFiles.length === 0;
}

// Remove file from selection
function removeFile(index) {
    selectedFiles.splice(index, 1);
    renderSelectedFiles();
    uploadButton.disabled = selectedFiles.length === 0;
}

// Render selected files
function renderSelectedFiles() {
    if (selectedFiles.length === 0) {
        selectedFilesContainer.innerHTML = '';
        return;
    }

    const filesHTML = selectedFiles.map((file, index) => `
        <div class="file-item">
            <span class="file-name">${file.name}</span>
            <span class="file-size">${formatFileSize(file.size)}</span>
            <button class="remove-file" onclick="removeFile(${index})">×</button>
        </div>
    `).join('');

    selectedFilesContainer.innerHTML = filesHTML;
}

// Format file size
function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
}

// Handle upload
async function handleUpload() {
    if (selectedFiles.length === 0) return;

    uploadButton.disabled = true;
    uploadProgressContainer.classList.remove('hidden');
    uploadProgressContainer.innerHTML = '';

    const customLabels = customLabelsInput.value.trim();

    for (let i = 0; i < selectedFiles.length; i++) {
        const file = selectedFiles[i];
        await uploadFile(file, customLabels, i);
    }

    // Clear selection after upload
    setTimeout(() => {
        selectedFiles = [];
        renderSelectedFiles();
        uploadButton.disabled = true;
        customLabelsInput.value = '';
        fileInput.value = '';
    }, 2000);
}

// Upload single file
async function uploadFile(file, customLabels, index) {
    const progressId = `progress-${index}`;

    // Create progress item
    const progressHTML = `
        <div class="progress-item" id="${progressId}">
            <div class="progress-header">
                <span class="progress-filename">${file.name}</span>
                <span class="progress-status">Uploading...</span>
            </div>
            <div class="progress-bar">
                <div class="progress-fill" style="width: 0%"></div>
            </div>
        </div>
    `;
    uploadProgressContainer.innerHTML += progressHTML;

    const progressItem = document.getElementById(progressId);
    const progressStatus = progressItem.querySelector('.progress-status');
    const progressFill = progressItem.querySelector('.progress-fill');

    try {
        // Generate unique filename
        const timestamp = Date.now();
        const filename = `${timestamp}-${file.name}`;

        // Prepare headers
        const headers = {
            'Content-Type': file.type
        };

        if (customLabels) {
            headers['x-amz-meta-customLabels'] = customLabels;
        }

        if (CONFIG.API_KEY) {
            headers['x-api-key'] = CONFIG.API_KEY;
        }

        // Update progress
        progressFill.style.width = '50%';

        // Upload to API Gateway (which proxies to S3)
        const response = await fetch(`${CONFIG.API_ENDPOINT}/photos/${filename}`, {
            method: 'PUT',
            headers: headers,
            body: file
        });

        if (response.ok) {
            progressFill.style.width = '100%';
            progressStatus.textContent = 'Success!';
            progressStatus.classList.add('success');
        } else {
            throw new Error(`Upload failed: ${response.statusText}`);
        }
    } catch (error) {
        console.error('Upload error:', error);
        progressStatus.textContent = 'Failed';
        progressStatus.classList.add('error');
        progressFill.style.width = '100%';
        progressFill.style.background = 'var(--error-color)';
    }
}

// Handle search
async function handleSearch() {
    const query = searchInput.value.trim();

    if (!query) {
        showError('Please enter a search query');
        return;
    }

    searchButton.disabled = true;
    searchButton.innerHTML = '<span>Searching...</span>';

    try {
        const headers = {
            'Content-Type': 'application/json'
        };

        if (CONFIG.API_KEY) {
            headers['x-api-key'] = CONFIG.API_KEY;
        }

        const response = await fetch(`${CONFIG.API_ENDPOINT}/search?q=${encodeURIComponent(query)}`, {
            method: 'GET',
            headers: headers
        });

        if (!response.ok) {
            throw new Error(`Search failed: ${response.statusText}`);
        }

        const data = await response.json();
        displayResults(data.results || []);
    } catch (error) {
        console.error('Search error:', error);
        showError('Search failed. Please try again.');
    } finally {
        searchButton.disabled = false;
        searchButton.innerHTML = `
            <span>Search</span>
            <svg class="btn-icon" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
            </svg>
        `;
    }
}

// Display search results
function displayResults(results) {
    if (results.length === 0) {
        resultsContainer.innerHTML = `
            <div class="no-results glass-card">
                <svg class="no-results-icon" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.172 16.172a4 4 0 015.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <h3>No photos found</h3>
                <p>Try a different search query</p>
            </div>
        `;
        return;
    }

    const resultsHTML = results.map(photo => `
        <div class="result-card">
            <img src="${photo.url}" alt="Photo" class="result-image" onerror="this.src='https://via.placeholder.com/300x250?text=Image+Not+Found'">
            <div class="result-content">
                <div class="result-labels">
                    ${photo.labels.map(label => `
                        <span class="label-tag">${label}</span>
                    `).join('')}
                </div>
            </div>
        </div>
    `).join('');

    resultsContainer.innerHTML = resultsHTML;
}

// Show error message
function showError(message) {
    resultsContainer.innerHTML = `
        <div class="no-results glass-card">
            <svg class="no-results-icon" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <h3>Error</h3>
            <p>${message}</p>
        </div>
    `;
}

// Initialize app
init();
