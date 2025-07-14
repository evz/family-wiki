/**
 * Main JavaScript for Family Wiki Tools
 */

function runTool(toolName) {
    const button = event.target;
    const originalText = button.getAttribute('data-original-text') || button.textContent;
    
    // Check if button is disabled
    if (button.disabled || button.classList.contains('btn-disabled')) {
        return;
    }
    
    // For extraction tool, check system status first
    if (toolName === 'extract') {
        fetch('/api/status')
            .then(response => response.json())
            .then(data => {
                if (!data.extraction_ready) {
                    let message = 'LLM Extraction is not available:\n\n';
                    if (!data.ollama.available) {
                        message += `• Ollama: ${data.ollama.message}\n`;
                        if (data.ollama.help) {
                            message += `  ${data.ollama.help}\n`;
                        }
                    }
                    if (!data.text_data.available) {
                        message += `• ${data.text_data.message}\n`;
                    }
                    alert(message);
                    return;
                }
                // If ready, proceed with extraction
                startToolExecution(toolName, button, originalText);
            })
            .catch(error => {
                alert(`Error checking system status: ${error}`);
            });
    } else {
        // For other tools, run directly
        startToolExecution(toolName, button, originalText);
    }
}

function startToolExecution(toolName, button, originalText) {
    // Update button state
    button.textContent = 'Running...';
    button.disabled = true;
    
    // Make API call
    fetch(`/api/run/${toolName}`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                if (data.task_id) {
                    // For extraction tool, start polling for status
                    button.textContent = 'Starting...';
                    pollExtractionStatus(data.task_id, button, originalText);
                } else {
                    // Show success message
                    alert(`${toolName.toUpperCase()} completed successfully!`);
                    button.textContent = originalText;
                    button.disabled = false;
                }
            } else {
                // Show error
                alert(`Error running ${toolName}: ${data.error || data.stderr}`);
                button.textContent = originalText;
                button.disabled = false;
            }
        })
        .catch(error => {
            alert(`Error: ${error}`);
            button.textContent = originalText;
            button.disabled = false;
        });
}

function pollExtractionStatus(taskId, button, originalText) {
    const checkStatus = () => {
        fetch(`/api/extraction/status/${taskId}`)
            .then(response => response.json())
            .then(data => {
                if (data.error) {
                    alert(`Extraction error: ${data.error}`);
                    button.textContent = originalText;
                    button.disabled = false;
                    return;
                }
                
                const status = data.status;
                const progress = data.progress || 0;
                
                if (status === 'pending') {
                    button.textContent = 'Pending...';
                } else if (status === 'running') {
                    button.textContent = `Processing... ${progress}%`;
                } else if (status === 'completed') {
                    button.textContent = 'Completed!';
                    setTimeout(() => {
                        button.textContent = originalText;
                        button.disabled = false;
                    }, 2000);
                    
                    // Show summary if available
                    if (data.summary) {
                        const summary = data.summary;
                        alert(`Extraction completed!\n\nFamilies: ${summary.total_families}\nPeople: ${summary.total_people}\nIsolated individuals: ${summary.total_isolated_individuals}`);
                    } else {
                        alert('Extraction completed successfully!');
                    }
                    return;
                } else if (status === 'failed') {
                    alert(`Extraction failed: ${data.error || 'Unknown error'}`);
                    button.textContent = originalText;
                    button.disabled = false;
                    return;
                }
                
                // Continue polling
                setTimeout(checkStatus, 2000);
            })
            .catch(error => {
                alert(`Error checking status: ${error}`);
                button.textContent = originalText;
                button.disabled = false;
            });
    };
    
    // Start polling
    checkStatus();
}

function refreshStatus() {
    fetch('/api/status/refresh')
        .then(response => response.json())
        .then(data => {
            // Reload the page to update the status display
            window.location.reload();
        })
        .catch(error => {
            alert(`Error refreshing status: ${error}`);
        });
}