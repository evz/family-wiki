/**
 * Simple JavaScript for Family Wiki Tools
 * ONLY handles extraction progress polling - everything else uses regular HTML forms
 */

function runExtraction() {
    const button = event.target;
    const originalText = button.getAttribute('data-original-text') || button.textContent;
    
    if (button.disabled) return;
    
    // Check if extraction is ready first
    fetch('/api/status')
        .then(response => response.json())
        .then(data => {
            if (!data.extraction_ready) {
                let message = 'LLM Extraction is not available:\n\n';
                if (!data.ollama.available) {
                    message += `• Ollama: ${data.ollama.message}\n`;
                }
                if (!data.text_data.available) {
                    message += `• ${data.text_data.message}\n`;
                }
                alert(message);
                return;
            }
            
            // Start extraction
            startExtraction(button, originalText);
        })
        .catch(error => {
            alert(`Error checking system status: ${error}`);
        });
}

function startExtraction(button, originalText) {
    button.textContent = 'Starting...';
    button.disabled = true;
    
    fetch('/api/extraction/start')
        .then(response => response.json())
        .then(data => {
            if (data.task_id) {
                pollExtractionStatus(data.task_id, button, originalText);
            } else {
                alert('Failed to start extraction');
                button.textContent = originalText;
                button.disabled = false;
            }
        })
        .catch(error => {
            alert(`Error starting extraction: ${error}`);
            button.textContent = originalText;
            button.disabled = false;
        });
}

function pollExtractionStatus(taskId, button, originalText) {
    const poll = () => {
        fetch(`/api/extraction/status/${taskId}`)
            .then(response => response.json())
            .then(data => {
                if (data.status === 'completed') {
                    button.textContent = 'Completed!';
                    if (data.summary) {
                        alert(`Extraction completed!\n\nFamilies: ${data.summary.total_families}\nPeople: ${data.summary.total_people}`);
                    }
                    setTimeout(() => {
                        button.textContent = originalText;
                        button.disabled = false;
                    }, 2000);
                } else if (data.status === 'failed') {
                    alert(`Extraction failed: ${data.error || 'Unknown error'}`);
                    button.textContent = originalText;
                    button.disabled = false;
                } else {
                    // Still running
                    const progress = data.progress || 0;
                    button.textContent = `Processing... ${progress}%`;
                    setTimeout(poll, 2000);
                }
            })
            .catch(error => {
                alert(`Error checking status: ${error}`);
                button.textContent = originalText;
                button.disabled = false;
            });
    };
    
    poll();
}