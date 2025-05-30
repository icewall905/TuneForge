// main.js - Main JavaScript for Ollama Playlist Generator

// Global variables
let currentModal = null;

// Dark mode toggle function
function toggleDarkMode() {
    const htmlElement = document.documentElement;
    const currentTheme = htmlElement.getAttribute('data-bs-theme');
    const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
    
    htmlElement.setAttribute('data-bs-theme', newTheme);
    localStorage.setItem('theme', newTheme);
    
    // Update any UI elements that need to change with the theme
    updateThemeUI(newTheme);
}

// Update UI elements based on theme
function updateThemeUI(theme) {
    // This function can be expanded as needed to update specific UI elements
    // based on the theme (e.g., icon changes, background images, etc.)
    
    // Example: Toggle theme button icon
    const darkIcon = document.getElementById('dark-icon');
    const lightIcon = document.getElementById('light-icon');
    
    if (darkIcon && lightIcon) {
        if (theme === 'dark') {
            darkIcon.style.display = 'none';
            lightIcon.style.display = 'block';
        } else {
            darkIcon.style.display = 'block';
            lightIcon.style.display = 'none';
        }
    }
}

// Initialize theme from localStorage or system preference
function initializeTheme() {
    const savedTheme = localStorage.getItem('theme');
    const htmlElement = document.documentElement;
    
    if (savedTheme) {
        htmlElement.setAttribute('data-bs-theme', savedTheme);
    } else {
        const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
        const initialTheme = prefersDark ? 'dark' : 'light';
        htmlElement.setAttribute('data-bs-theme', initialTheme);
        localStorage.setItem('theme', initialTheme);
    }
    
    updateThemeUI(htmlElement.getAttribute('data-bs-theme'));
}

// Generic modal functionality
function showModal(modalId, config = {}) {
    const modal = document.getElementById(modalId);
    if (!modal) return;
    
    // Apply configuration
    if (config.title) {
        const titleElement = modal.querySelector('.modal-title');
        if (titleElement) titleElement.textContent = config.title;
    }
    
    if (config.content) {
        const contentElement = modal.querySelector('.modal-content-body');
        if (contentElement) contentElement.innerHTML = config.content;
    }
    
    // Show the modal
    modal.style.display = 'block';
    currentModal = modal;
    
    // Handle callback if provided
    if (config.onShow && typeof config.onShow === 'function') {
        config.onShow(modal);
    }
}

function hideModal(modalId) {
    const modal = modalId ? document.getElementById(modalId) : currentModal;
    if (modal) {
        modal.style.display = 'none';
        currentModal = null;
    }
}

// Close modal when clicking outside of it
window.addEventListener('click', function(event) {
    if (currentModal && event.target === currentModal) {
        hideModal();
    }
});

// Initialize when the DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    initializeTheme();
    
    // Add event listener to theme toggle button if it exists
    const themeToggleBtn = document.getElementById('theme-toggle-btn');
    if (themeToggleBtn) {
        themeToggleBtn.addEventListener('click', toggleDarkMode);
    }
    
    // Add other initialization code here
});
