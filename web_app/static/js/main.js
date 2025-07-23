/**
 * Task Status Polling for Family Wiki Tools
 * ONLY handles Celery task status polling - job submission handled by forms
 */

function pollTaskStatus(taskId, taskType, updateCallback) {
    const poll = () => {
        fetch(`/api/jobs/${taskId}/status`)
            .then(response => response.json())
            .then(data => {
                if (data.status === 'completed') {
                    updateCallback('completed', data);
                } else if (data.status === 'failed') {
                    updateCallback('failed', data);
                } else {
                    // Still running
                    updateCallback('running', data);
                    setTimeout(poll, 2000);
                }
            })
            .catch(error => {
                updateCallback('error', { error: error.message });
            });
    };
    
    poll();
}