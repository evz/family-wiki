/**
 * Main JavaScript for Family Wiki Tools
 */

// Global configuration
const Config = {
    API_BASE: '/api',
    POLL_INTERVAL: 2000, // 2 seconds
    TASK_TIMEOUT: 3600000 // 1 hour
};

// Utility functions
const Utils = {
    /**
     * Show a status message
     */
    showStatus(message, type = 'info') {
        const statusDiv = document.createElement('div');
        statusDiv.className = `status ${type}`;
        statusDiv.textContent = message;
        
        const container = document.querySelector('.container');
        const header = container.querySelector('.header');
        header.after(statusDiv);
        
        // Auto-remove after 5 seconds
        setTimeout(() => {
            if (statusDiv.parentNode) {
                statusDiv.remove();
            }
        }, 5000);
    },

    /**
     * Format elapsed time
     */
    formatElapsedTime(seconds) {
        const minutes = Math.floor(seconds / 60);
        const remainingSeconds = seconds % 60;
        return `${minutes}m ${remainingSeconds}s`;
    },

    /**
     * Make API request with error handling
     */
    async apiRequest(url, options = {}) {
        try {
            const response = await fetch(url, {
                headers: {
                    'Content-Type': 'application/json',
                    ...options.headers
                },
                ...options
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            return await response.json();
        } catch (error) {
            console.error('API request failed:', error);
            throw error;
        }
    }
};

// Tool execution for simple tools (non-extract)
function runTool(tool, verbose = false) {
    // Special handling for extract tool
    if (tool === 'extract') {
        if (window.ExtractionManager) {
            window.ExtractionManager.startExtraction(verbose);
        } else {
            Utils.showStatus('Extraction manager not loaded', 'error');
        }
        return;
    }

    const btn = event.target;
    const originalText = btn.dataset.originalText || btn.textContent;
    
    btn.disabled = true;
    btn.textContent = 'Running...';
    
    // Show output section if it exists
    const outputSection = document.getElementById('output-section');
    const toolOutput = document.getElementById('tool-output');
    
    if (outputSection) {
        outputSection.style.display = 'block';
        outputSection.classList.add('fade-in');
    }
    
    if (toolOutput) {
        toolOutput.textContent = 'Starting...\n';
    }
    
    const url = `${Config.API_BASE}/run/${tool}${verbose ? '?verbose=1' : ''}`;
    
    Utils.apiRequest(url)
        .then(data => {
            if (toolOutput) {
                if (data.success) {
                    toolOutput.textContent = `✅ Tool completed successfully!\n\nOutput:\n${data.stdout}`;
                    if (data.stderr) {
                        toolOutput.textContent += `\n\nWarnings:\n${data.stderr}`;
                    }
                    Utils.showStatus(`${tool} completed successfully`, 'success');
                } else {
                    toolOutput.textContent = `❌ Tool failed!\n\nError:\n${data.stderr || data.error}`;
                    if (data.stdout) {
                        toolOutput.textContent += `\n\nOutput:\n${data.stdout}`;
                    }
                    Utils.showStatus(`${tool} failed`, 'error');
                }
            }
        })
        .catch(error => {
            if (toolOutput) {
                toolOutput.textContent = `❌ Network Error: ${error.message}`;
            }
            Utils.showStatus(`Error running ${tool}: ${error.message}`, 'error');
        })
        .finally(() => {
            btn.disabled = false;
            btn.textContent = originalText;
        });
}

// Initialize page
document.addEventListener('DOMContentLoaded', function() {
    console.log('Family Wiki Tools loaded');
    
    // Add smooth scrolling to anchor links
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });
    
    // Add keyboard shortcuts
    document.addEventListener('keydown', function(e) {
        // Ctrl/Cmd + K to focus search (if we add search later)
        if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
            e.preventDefault();
            // Focus search input when we add it
        }
        
        // Escape to close modals/dialogs
        if (e.key === 'Escape') {
            // Close any open modals
            const openModals = document.querySelectorAll('.modal.open');
            openModals.forEach(modal => modal.classList.remove('open'));
        }
    });
});

// CLI Help function
function showCLIHelp() {
    const helpText = `
Family Wiki CLI Commands:

Basic Commands:
• flask ocr           - Extract text from PDFs using OCR
• flask extract       - AI-powered genealogy extraction  
• flask gedcom        - Generate GEDCOM files
• flask research      - Generate research questions
• flask benchmark     - Test LLM models
• flask pipeline      - Run complete workflow
• flask run           - Start web interface
• flask status        - Check system status

Options:
• Add --verbose or -v to any command for detailed output
• Example: flask extract --verbose

Setup:
1. source .venv/bin/activate
2. export FLASK_APP=app.py
3. flask --help (for more options)

Web Interface: http://localhost:5000
    `;
    
    // Create modal
    const modal = document.createElement('div');
    modal.style.cssText = `
        position: fixed; top: 0; left: 0; width: 100%; height: 100%;
        background: rgba(0,0,0,0.5); display: flex; align-items: center; 
        justify-content: center; z-index: 1000;
    `;
    
    const content = document.createElement('div');
    content.style.cssText = `
        background: white; padding: 2rem; border-radius: 8px; 
        max-width: 600px; max-height: 80vh; overflow-y: auto;
        position: relative;
    `;
    
    content.innerHTML = `
        <h3>Family Wiki CLI Commands</h3>
        <pre style="white-space: pre-wrap; font-family: monospace; background: #f8f9fa; padding: 1rem; border-radius: 4px;">${helpText}</pre>
        <button onclick="this.closest('.modal').remove()" class="btn">Close</button>
    `;
    
    modal.className = 'modal';
    modal.appendChild(content);
    document.body.appendChild(modal);
    
    // Close on background click
    modal.addEventListener('click', (e) => {
        if (e.target === modal) modal.remove();
    });
}

// Export for use in other scripts
window.FamilyWiki = {
    Config,
    Utils,
    runTool
};

// Add to global scope for template use
window.showCLIHelp = showCLIHelp;