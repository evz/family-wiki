/**
 * Jest setup file for Family Wiki JavaScript tests
 */

// Add custom matchers from testing-library
require('@testing-library/jest-dom');

// Mock fetch globally
global.fetch = jest.fn();

// Mock alert and console methods
global.alert = jest.fn();
global.console = {
  ...console,
  log: jest.fn(),
  error: jest.fn(),
  warn: jest.fn(),
};

// Mock window.location
delete window.location;
window.location = {
  href: '',
  reload: jest.fn(),
};

// Mock setTimeout and clearTimeout for tests
jest.useFakeTimers();

// Reset all mocks before each test
beforeEach(() => {
  fetch.mockClear();
  alert.mockClear();
  console.log.mockClear();
  console.error.mockClear();
  console.warn.mockClear();
  window.location.reload.mockClear();
  
  // Reset DOM
  document.body.innerHTML = '';
  
  // Reset timers
  jest.clearAllTimers();
});