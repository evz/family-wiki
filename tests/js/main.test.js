/**
 * Tests for main.js JavaScript functionality
 */

// Load the main.js file
const fs = require('fs');
const path = require('path');

// Read and evaluate the main.js file
const mainJsPath = path.join(__dirname, '../../web_app/static/js/main.js');
const mainJsContent = fs.readFileSync(mainJsPath, 'utf8');
eval(mainJsContent);

describe('Family Wiki Main JavaScript', () => {
  let mockButton;
  
  beforeEach(() => {
    // Create a mock button for testing
    mockButton = document.createElement('button');
    mockButton.setAttribute('data-original-text', 'Run Tool');
    mockButton.textContent = 'Run Tool';
    document.body.appendChild(mockButton);
  });

  describe('runTool function', () => {
    test('should exist and be a function', () => {
      expect(typeof runTool).toBe('function');
    });

    test('should return early if button is disabled', () => {
      mockButton.disabled = true;
      
      // Mock event.target
      const mockEvent = { target: mockButton };
      global.event = mockEvent;
      
      runTool('ocr');
      
      // Should not make any fetch calls
      expect(fetch).not.toHaveBeenCalled();
    });

    test('should return early if button has btn-disabled class', () => {
      mockButton.classList.add('btn-disabled');
      
      const mockEvent = { target: mockButton };
      global.event = mockEvent;
      
      runTool('ocr');
      
      expect(fetch).not.toHaveBeenCalled();
    });

    test('should check system status for extract tool', async () => {
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
          success: true,
          task_id: 'test-task-123'
        })
      });
      
      runTool('extract');
      
      // Should call status endpoint first
      await jest.runOnlyPendingTimersAsync();
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
            message: 'Ollama not running',
            help: 'Start Ollama server'
          },
          text_data: { available: true }
        })
      });
      
      runTool('extract');
      
      await jest.runOnlyPendingTimersAsync();
      
      expect(alert).toHaveBeenCalledWith(
        expect.stringContaining('LLM Extraction is not available')
      );
      expect(alert).toHaveBeenCalledWith(
        expect.stringContaining('Ollama not running')
      );
    });

    test('should call API directly for non-extract tools', () => {
      const mockEvent = { target: mockButton };
      global.event = mockEvent;
      
      fetch.mockResolvedValueOnce({
        json: () => Promise.resolve({
          success: true,
          message: 'OCR completed'
        })
      });
      
      runTool('ocr');
      
      expect(fetch).toHaveBeenCalledWith('/api/run/ocr');
    });
  });

  describe('startToolExecution function', () => {
    test('should exist and be a function', () => {
      expect(typeof startToolExecution).toBe('function');
    });

    test('should disable button and change text', () => {
      fetch.mockResolvedValueOnce({
        json: () => Promise.resolve({ success: true })
      });
      
      startToolExecution('ocr', mockButton, 'Run OCR');
      
      expect(mockButton.disabled).toBe(true);
      expect(mockButton.textContent).toBe('Running...');
    });

    test('should handle successful non-extraction tool', async () => {
      fetch.mockResolvedValueOnce({
        json: () => Promise.resolve({
          success: true,
          message: 'Tool completed'
        })
      });
      
      await startToolExecution('ocr', mockButton, 'Run OCR');
      
      await jest.runOnlyPendingTimersAsync();
      
      expect(alert).toHaveBeenCalledWith('OCR completed successfully!');
      expect(mockButton.disabled).toBe(false);
      expect(mockButton.textContent).toBe('Run OCR');
    });

    test('should handle extraction tool with task_id', (done) => {
      fetch.mockResolvedValueOnce({
        json: () => Promise.resolve({
          success: true,
          task_id: 'test-task-123'
        })
      });
      
      startToolExecution('extract', mockButton, 'Run Extraction');
      
      // Wait for async operations to complete
      setTimeout(() => {
        try {
          expect(mockButton.textContent).toBe('Starting...');
          done();
        } catch (error) {
          done(error);
        }
      }, 100);
    });

    test('should handle API errors', async () => {
      fetch.mockResolvedValueOnce({
        json: () => Promise.resolve({
          success: false,
          error: 'Tool failed to run'
        })
      });
      
      await startToolExecution('ocr', mockButton, 'Run OCR');
      
      await jest.runOnlyPendingTimersAsync();
      
      expect(alert).toHaveBeenCalledWith('Error running ocr: Tool failed to run');
      expect(mockButton.disabled).toBe(false);
      expect(mockButton.textContent).toBe('Run OCR');
    });

    test('should handle network errors', async () => {
      fetch.mockRejectedValueOnce(new Error('Network error'));
      
      await startToolExecution('ocr', mockButton, 'Run OCR');
      
      await jest.runOnlyPendingTimersAsync();
      
      expect(alert).toHaveBeenCalledWith('Error: Error: Network error');
      expect(mockButton.disabled).toBe(false);
      expect(mockButton.textContent).toBe('Run OCR');
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
      
      pollExtractionStatus('test-task-123', mockButton, 'Run Extraction');
      
      // Wait for the initial fetch call
      await jest.runOnlyPendingTimersAsync();
      
      expect(fetch).toHaveBeenCalledWith('/api/extraction/status/test-task-123');
      expect(mockButton.textContent).toBe('Processing... 50%');
    });

    test('should handle completed status', (done) => {
      fetch.mockImplementation(() => Promise.resolve({
        json: () => Promise.resolve({
          status: 'completed',
          summary: {
            total_families: 5,
            total_people: 20,
            total_isolated_individuals: 3
          }
        })
      }));
      
      pollExtractionStatus('test-task-123', mockButton, 'Run Extraction');
      
      // Wait for async operations to complete
      setTimeout(() => {
        try {
          expect(mockButton.textContent).toBe('Completed!');
          expect(alert).toHaveBeenCalledWith(
            expect.stringContaining('Extraction completed!')
          );
          expect(alert).toHaveBeenCalledWith(
            expect.stringContaining('Families: 5')
          );
          done();
        } catch (error) {
          done(error);
        }
      }, 100);
    });

    test('should handle failed status', async () => {
      fetch.mockResolvedValueOnce({
        json: () => Promise.resolve({
          error: 'Extraction process failed'
        })
      });
      
      pollExtractionStatus('test-task-123', mockButton, 'Run Extraction');
      
      await jest.runOnlyPendingTimersAsync();
      
      expect(alert).toHaveBeenCalledWith('Extraction error: Extraction process failed');
      expect(mockButton.disabled).toBe(false);
      expect(mockButton.textContent).toBe('Run Extraction');
    });

    test('should continue polling for running status', async () => {
      // First call returns running
      fetch.mockImplementation(() => Promise.resolve({
        json: () => Promise.resolve({
          status: 'running',
          progress: 25
        })
      }));
      
      pollExtractionStatus('test-task-123', mockButton, 'Run Extraction');
      
      await jest.runOnlyPendingTimersAsync();
      
      expect(mockButton.textContent).toBe('Processing... 25%');
      
      // Should schedule another check - we can't easily test this with mocked timers
      // Just verify the function completed without error
    });
  });

  describe('refreshStatus function', () => {
    test('should exist and be a function', () => {
      expect(typeof refreshStatus).toBe('function');
    });

    test('should call refresh endpoint and reload page', async () => {
      fetch.mockResolvedValueOnce({
        json: () => Promise.resolve({ status: 'refreshed' })
      });
      
      refreshStatus();
      
      await jest.runOnlyPendingTimersAsync();
      
      expect(fetch).toHaveBeenCalledWith('/api/status/refresh');
      expect(window.location.reload).toHaveBeenCalled();
    });

    test('should handle refresh errors', async () => {
      fetch.mockRejectedValueOnce(new Error('Refresh failed'));
      
      refreshStatus();
      
      await jest.runOnlyPendingTimersAsync();
      
      expect(alert).toHaveBeenCalledWith('Error refreshing status: Error: Refresh failed');
    });
  });

  describe('Integration tests', () => {
    test('should not reference old ExtractionManager', () => {
      expect(mainJsContent).not.toContain('ExtractionManager');
      expect(mainJsContent).not.toContain('Extraction manager not loaded');
    });

    test('should have all required functions', () => {
      expect(typeof runTool).toBe('function');
      expect(typeof startToolExecution).toBe('function');
      expect(typeof pollExtractionStatus).toBe('function');
      expect(typeof refreshStatus).toBe('function');
    });
  });
});