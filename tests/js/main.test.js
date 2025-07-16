/**
 * Tests for simplified main.js JavaScript functionality
 * Only tests extraction progress polling - everything else uses basic HTML forms
 */

// Load the main.js file
const fs = require('fs');
const path = require('path');

const mainJsPath = path.join(__dirname, '../../web_app/static/js/main.js');
const mainJsContent = fs.readFileSync(mainJsPath, 'utf8');
eval(mainJsContent);

describe('Family Wiki Simplified JavaScript', () => {
  let mockButton;
  
  beforeEach(() => {
    // Create a mock button for testing
    mockButton = document.createElement('button');
    mockButton.setAttribute('data-original-text', 'Start Extraction');
    mockButton.textContent = 'Start Extraction';
    document.body.appendChild(mockButton);
  });

  describe('runExtraction function', () => {
    test('should exist and be a function', () => {
      expect(typeof runExtraction).toBe('function');
    });

    test('should return early if button is disabled', () => {
      mockButton.disabled = true;
      
      // Mock event.target
      const mockEvent = { target: mockButton };
      global.event = mockEvent;
      
      runExtraction();
      
      // Should not make any fetch calls
      expect(fetch).not.toHaveBeenCalled();
    });

    test('should check system status before starting extraction', async () => {
      const mockEvent = { target: mockButton };
      global.event = mockEvent;
      
      // Mock successful status check
      fetch.mockResolvedValueOnce({
        json: () => Promise.resolve({
          extraction_ready: true,
          ollama: { available: true },
          text_data: { available: true }
        })
      });
      
      // Mock successful extraction start
      fetch.mockResolvedValueOnce({
        json: () => Promise.resolve({
          task_id: 'test-task-123'
        })
      });
      
      runExtraction();
      
      await jest.runOnlyPendingTimersAsync();
      
      // Should call status endpoint first
      expect(fetch).toHaveBeenCalledWith('/api/status');
    });

    test('should show alert when extraction not ready', async () => {
      const mockEvent = { target: mockButton };
      global.event = mockEvent;
      
      fetch.mockResolvedValueOnce({
        json: () => Promise.resolve({
          extraction_ready: false,
          ollama: { 
            available: false, 
            message: 'Ollama not running'
          },
          text_data: { available: true }
        })
      });
      
      runExtraction();
      
      await jest.runOnlyPendingTimersAsync();
      
      expect(alert).toHaveBeenCalledWith(
        expect.stringContaining('LLM Extraction is not available')
      );
      expect(alert).toHaveBeenCalledWith(
        expect.stringContaining('Ollama not running')
      );
    });
  });

  describe('startExtraction function', () => {
    test('should exist and be a function', () => {
      expect(typeof startExtraction).toBe('function');
    });

    test('should disable button and change text', () => {
      fetch.mockResolvedValueOnce({
        json: () => Promise.resolve({ task_id: 'test-task-123' })
      });
      
      startExtraction(mockButton, 'Start Extraction');
      
      expect(mockButton.disabled).toBe(true);
      expect(mockButton.textContent).toBe('Starting...');
    });

    test('should handle successful extraction start', async () => {
      fetch.mockResolvedValueOnce({
        json: () => Promise.resolve({
          task_id: 'test-task-123'
        })
      });
      
      await startExtraction(mockButton, 'Start Extraction');
      
      expect(fetch).toHaveBeenCalledWith('/api/extraction/start');
    });

    test('should handle extraction start errors', async () => {
      fetch.mockRejectedValueOnce(new Error('Network error'));
      
      await startExtraction(mockButton, 'Start Extraction');
      
      await jest.runOnlyPendingTimersAsync();
      
      expect(alert).toHaveBeenCalledWith('Error starting extraction: Error: Network error');
      expect(mockButton.disabled).toBe(false);
      expect(mockButton.textContent).toBe('Start Extraction');
    });
  });

  describe('pollExtractionStatus function', () => {
    test('should exist and be a function', () => {
      expect(typeof pollExtractionStatus).toBe('function');
    });

    test('should poll status and update button text', async () => {
      fetch.mockImplementation(() => Promise.resolve({
        json: () => Promise.resolve({
          status: 'running',
          progress: 50
        })
      }));
      
      pollExtractionStatus('test-task-123', mockButton, 'Start Extraction');
      
      await jest.runOnlyPendingTimersAsync();
      
      expect(fetch).toHaveBeenCalledWith('/api/extraction/status/test-task-123');
      expect(mockButton.textContent).toBe('Processing... 50%');
    });

    test('should handle completed status', async () => {
      fetch.mockImplementation(() => Promise.resolve({
        json: () => Promise.resolve({
          status: 'completed',
          summary: {
            total_families: 5,
            total_people: 20
          }
        })
      }));
      
      pollExtractionStatus('test-task-123', mockButton, 'Start Extraction');
      
      await jest.runOnlyPendingTimersAsync();
      
      expect(mockButton.textContent).toBe('Completed!');
      expect(alert).toHaveBeenCalledWith(
        expect.stringContaining('Extraction completed!')
      );
      expect(alert).toHaveBeenCalledWith(
        expect.stringContaining('Families: 5')
      );
    });

    test('should handle failed status', async () => {
      fetch.mockResolvedValueOnce({
        json: () => Promise.resolve({
          status: 'failed',
          error: 'Extraction process failed'
        })
      });
      
      pollExtractionStatus('test-task-123', mockButton, 'Start Extraction');
      
      await jest.runOnlyPendingTimersAsync();
      
      expect(alert).toHaveBeenCalledWith('Extraction failed: Extraction process failed');
      expect(mockButton.disabled).toBe(false);
      expect(mockButton.textContent).toBe('Start Extraction');
    });
  });

  describe('Integration tests', () => {
    test('should only have extraction-related functions', () => {
      expect(typeof runExtraction).toBe('function');
      expect(typeof startExtraction).toBe('function');
      expect(typeof pollExtractionStatus).toBe('function');
    });

    test('should use correct API endpoints', () => {
      expect(mainJsContent).toContain('/api/extraction/status/');
      expect(mainJsContent).toContain('/api/extraction/start');
      expect(mainJsContent).toContain('/api/status');
    });

    test('should not contain complex framework code', () => {
      expect(mainJsContent).not.toContain('FamilyWiki.Config');
      expect(mainJsContent).not.toContain('PromptsManager');
      expect(mainJsContent).not.toContain('class ');
    });
  });
});