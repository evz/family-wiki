/**
 * JavaScript for LLM Extraction tool with progress tracking
 */

class ExtractionManager {
    constructor() {
        this.currentTaskId = null;
        this.pollInterval = null;
        this.isRunning = false;
        
        // DOM elements
        this.outputSection = document.getElementById('output-section');
        this.progressBar = document.getElementById('progress-bar');
        this.progressFill = document.getElementById('progress-fill');
        this.progressText = document.getElementById('progress-text');
        this.toolOutput = document.getElementById('tool-output');
        this.extractionSummary = document.getElementById('extraction-summary');
        
        this.init();
    }
    
    init() {
        console.log('Extraction manager initialized');
        
        // Add event listeners for cleanup
        window.addEventListener('beforeunload', () => {
            this.cleanup();
        });
    }
    
    async startExtraction(verbose = false) {
        if (this.isRunning) {
            FamilyWiki.Utils.showStatus('Extraction already running', 'error');
            return;
        }
        
        const btn = event.target;
        const originalText = btn.dataset.originalText || btn.textContent;
        
        try {
            this.isRunning = true;
            this.resetUI();
            this.showProgress();
            
            btn.disabled = true;
            btn.textContent = 'Starting Extraction...';
            
            // Start extraction
            const startResponse = await FamilyWiki.Utils.apiRequest(
                `${FamilyWiki.Config.API_BASE}/extraction/start${verbose ? '?verbose=1' : ''}`
            );
            
            if (!startResponse.task_id) {
                throw new Error('No task ID received from server');
            }
            
            this.currentTaskId = startResponse.task_id;
            this.updateProgress({
                status: 'starting',
                progress: 0,
                current_chunk: 0,
                total_chunks: 0
            });
            
            // Start polling for progress
            this.startPolling(btn, originalText);
            
        } catch (error) {
            console.error('Failed to start extraction:', error);
            this.handleError(`Failed to start extraction: ${error.message}`, btn, originalText);
        }
    }
    
    startPolling(btn, originalText) {
        if (this.pollInterval) {
            clearInterval(this.pollInterval);
        }
        
        this.pollInterval = setInterval(async () => {
            try {
                const status = await FamilyWiki.Utils.apiRequest(
                    `${FamilyWiki.Config.API_BASE}/extraction/status/${this.currentTaskId}`
                );
                
                this.updateProgress(status);
                
                if (status.status === 'completed') {
                    this.handleCompletion(status, btn, originalText);
                } else if (status.status === 'failed') {
                    this.handleFailure(status, btn, originalText);
                }
                
            } catch (error) {
                console.error('Error polling status:', error);
                this.handleError(`Error checking progress: ${error.message}`, btn, originalText);
            }
        }, FamilyWiki.Config.POLL_INTERVAL);
        
        // Set timeout to prevent infinite polling
        setTimeout(() => {
            if (this.pollInterval) {
                this.handleError('Extraction timed out', btn, originalText);
            }
        }, FamilyWiki.Config.TASK_TIMEOUT);
    }
    
    updateProgress(status) {
        if (!this.progressText || !this.progressFill) return;
        
        const btn = document.querySelector('button[disabled]');
        
        switch (status.status) {
            case 'starting':
                this.progressText.textContent = 'Initializing extraction...';
                if (btn) btn.textContent = 'Initializing...';
                this.progressFill.style.width = '5%';
                break;
                
            case 'running':
                const elapsed = status.elapsed_seconds || 0;
                const currentChunk = status.current_chunk || 0;
                const totalChunks = status.total_chunks || 0;
                
                let progressText = `Processing...`;
                if (totalChunks > 0) {
                    progressText += ` (${currentChunk}/${totalChunks} chunks)`;
                }
                if (elapsed > 0) {
                    progressText += ` - ${FamilyWiki.Utils.formatElapsedTime(elapsed)} elapsed`;
                }
                
                this.progressText.textContent = progressText;
                
                if (btn) {
                    btn.textContent = `Processing... (${FamilyWiki.Utils.formatElapsedTime(elapsed)})`;
                }
                
                // Calculate progress
                let progress = status.progress || 0;
                if (totalChunks > 0 && currentChunk > 0) {
                    progress = Math.max(progress, (currentChunk / totalChunks) * 90);
                }
                
                this.progressFill.style.width = `${Math.min(95, progress)}%`;
                break;
        }
        
        // Update output with latest info
        if (this.toolOutput) {
            let output = `Status: ${status.status}\n`;
            if (status.current_chunk && status.total_chunks) {
                output += `Progress: ${status.current_chunk}/${status.total_chunks} chunks\n`;
            }
            if (status.elapsed_seconds) {
                output += `Elapsed: ${FamilyWiki.Utils.formatElapsedTime(status.elapsed_seconds)}\n`;
            }
            output += '\nProcessing family genealogy data...\n';
            
            this.toolOutput.textContent = output;
        }
    }
    
    handleCompletion(status, btn, originalText) {
        this.cleanup();
        
        this.progressFill.style.width = '100%';
        this.progressText.textContent = 'Extraction completed successfully!';
        
        if (this.toolOutput) {
            let output = '✅ Extraction completed successfully!\n\n';
            
            if (status.result) {
                output += `Results:\n`;
                output += `- Total families: ${status.result.total_families || 0}\n`;
                output += `- Total people: ${status.result.total_people || 0}\n`;
                output += `- Isolated individuals: ${status.result.total_isolated_individuals || 0}\n\n`;
            }
            
            if (status.duration_seconds) {
                output += `Completed in ${FamilyWiki.Utils.formatElapsedTime(status.duration_seconds)}\n`;
            }
            
            this.toolOutput.textContent = output;
        }
        
        // Show summary if available
        if (status.summary) {
            this.displaySummary(status.summary);
        }
        
        btn.disabled = false;
        btn.textContent = originalText;
        
        FamilyWiki.Utils.showStatus('Extraction completed successfully!', 'success');
    }
    
    handleFailure(status, btn, originalText) {
        this.cleanup();
        
        if (this.toolOutput) {
            this.toolOutput.textContent = `❌ Extraction failed!\n\nError: ${status.error || 'Unknown error'}`;
        }
        
        btn.disabled = false;
        btn.textContent = originalText;
        
        FamilyWiki.Utils.showStatus(`Extraction failed: ${status.error || 'Unknown error'}`, 'error');
    }
    
    handleError(message, btn, originalText) {
        this.cleanup();
        
        if (this.toolOutput) {
            this.toolOutput.textContent = `❌ ${message}`;
        }
        
        if (this.progressBar) {
            this.progressBar.style.display = 'none';
        }
        
        btn.disabled = false;
        btn.textContent = originalText;
        
        FamilyWiki.Utils.showStatus(message, 'error');
    }
    
    displaySummary(summary) {
        if (!this.extractionSummary) return;
        
        this.extractionSummary.style.display = 'block';
        this.extractionSummary.classList.add('fade-in');
        
        // Update summary cards
        const updates = {
            'summary-families': summary.total_families || 0,
            'summary-people': summary.total_people || 0,
            'summary-isolated': summary.total_isolated_individuals || 0,
            'summary-avg-children': (summary.avg_children_per_family || 0).toFixed(1),
            'summary-with-parents': summary.families_with_parents || 0,
            'summary-with-generation': summary.families_with_generation || 0
        };
        
        for (const [id, value] of Object.entries(updates)) {
            const element = document.getElementById(id);
            if (element) {
                // Animate number change
                this.animateNumber(element, value);
            }
        }
    }
    
    animateNumber(element, targetValue) {
        const currentValue = parseFloat(element.textContent) || 0;
        const isDecimal = targetValue.toString().includes('.');
        const duration = 1000; // 1 second
        const steps = 30;
        const stepValue = (targetValue - currentValue) / steps;
        const stepDuration = duration / steps;
        
        let step = 0;
        const timer = setInterval(() => {
            step++;
            const value = currentValue + (stepValue * step);
            
            if (step >= steps) {
                element.textContent = targetValue;
                clearInterval(timer);
            } else {
                element.textContent = isDecimal ? value.toFixed(1) : Math.round(value);
            }
        }, stepDuration);
    }
    
    resetUI() {
        if (this.outputSection) {
            this.outputSection.style.display = 'block';
            this.outputSection.classList.add('fade-in');
        }
        
        if (this.extractionSummary) {
            this.extractionSummary.style.display = 'none';
        }
        
        if (this.progressFill) {
            this.progressFill.style.width = '0%';
        }
        
        if (this.progressText) {
            this.progressText.textContent = '';
        }
        
        if (this.toolOutput) {
            this.toolOutput.textContent = 'Starting extraction...\n';
        }
    }
    
    showProgress() {
        if (this.progressBar) {
            this.progressBar.style.display = 'block';
            this.progressBar.classList.add('fade-in');
        }
    }
    
    cleanup() {
        this.isRunning = false;
        this.currentTaskId = null;
        
        if (this.pollInterval) {
            clearInterval(this.pollInterval);
            this.pollInterval = null;
        }
    }
}

// Initialize extraction manager when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    if (document.getElementById('extraction-summary')) {
        window.ExtractionManager = new ExtractionManager();
        console.log('Extraction manager ready');
    }
});