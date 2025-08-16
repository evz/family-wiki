# Testing Reform Action Plan

## Overview
This document outlines the step-by-step plan to bring the Family Wiki project's testing approach into line with the quality standards documented in `CLAUDE.md` and `TESTING_LESSONS_LEARNED.md`.

## Current Status
- ✅ OCR Task Manager bug fixed (missing `output_folder` attribute)
- ✅ Smoke test suite created (`smoke_tests.py`)
- ✅ Quality protocols documented (`CLAUDE.md`)
- ✅ Lessons learned documented (`TESTING_LESSONS_LEARNED.md`)
- ❌ **625 tests still using over-mocking patterns**
- ❌ **Celery test configuration still broken**
- ❌ **No real end-to-end integration tests**

## Phase 1: Infrastructure Fixes (HIGH PRIORITY - ~2 hours)

### 1.1 Fix Celery Test Configuration
**File:** `tests/conftest.py`
**Issue:** Tasks sent to Redis instead of running synchronously
**Fix:** Add to `BaseTestConfig`:
```python
# Celery configuration for synchronous testing
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True
CELERY_BROKER_URL = 'memory://'
CELERY_RESULT_BACKEND = 'cache+memory://'
```

### 1.2 Enhance and Integrate Smoke Tests  
**Files:** `smoke_tests.py`, `Makefile`, `pytest.ini`, CI configuration
**Goal:** Create more comprehensive smoke tests that generate realistic traffic

**Enhanced Smoke Test Requirements:**
- **Fake Traffic Generation**: Create realistic user workflows with actual data
- **Database State Testing**: Verify data persistence and retrieval  
- **File Upload/Download Flows**: Test with real temporary files
- **API Endpoint Coverage**: Hit all major routes with realistic payloads
- **Error Path Testing**: Verify error handling doesn't crash the app

**Implementation:**
```python
# Enhanced smoke_tests.py structure
class SmokeTestSuite:
    def test_full_ocr_workflow(self):
        """Generate fake PDF, process through OCR, verify results"""
        
    def test_rag_corpus_lifecycle(self): 
        """Create corpus, add documents, query, verify responses"""
        
    def test_genealogy_extraction_flow(self):
        """Process sample Dutch text through full extraction pipeline"""
        
    def test_concurrent_task_handling(self):
        """Submit multiple tasks simultaneously, verify no crashes"""
```

**Makefile targets:**
```bash
# Makefile  
smoke-test-basic:
	@echo "Running basic smoke tests..."
	@source .venv/bin/activate && set -a && source .env && set +a && python smoke_tests.py

smoke-test-traffic:
	@echo "Generating fake traffic and testing workflows..."
	@source .venv/bin/activate && set -a && source .env && set +a && python smoke_tests.py --traffic-test

test-integration: smoke-test-traffic
	@echo "Running full test suite after enhanced smoke tests pass..."
	@source .venv/bin/activate && pytest
```

### 1.3 Update pytest Configuration
**File:** `pytest.ini`
**Add:**
```ini
markers =
    smoke: smoke tests for basic functionality
    integration: real end-to-end workflow tests
    unit: isolated unit tests
    over_mocked: tests that need refactoring (temporary marker)
```

## Phase 2: Create Real Integration Tests (MEDIUM PRIORITY - ~4 hours)

### 2.1 OCR Workflow Integration Test
**File:** `tests/test_integration_ocr.py` (NEW)
**Test:** Real PDF upload → OCR processing → results download
```python
def test_ocr_workflow_end_to_end(client, temp_pdf_file):
    """Test complete OCR workflow without mocking internal logic"""
    # Real workflow: upload → process → results
    # Mock only external dependencies (file system, not TaskManager)
```

### 2.2 RAG Workflow Integration Test
**File:** `tests/test_integration_rag.py` (NEW)  
**Test:** Corpus creation → processing → query → results

**⚠️ CRITICAL DEPENDENCY: Ollama Server Setup**

**Local Development:**
- Uses existing Ollama installation on development machine
- Integration tests can run against real Ollama server

**CI/CD Environment Options:**
1. **Docker Container Approach** (Recommended):
   ```yaml
   # docker-compose.test.yml
   services:
     ollama:
       image: ollama/ollama:latest
       ports:
         - "11434:11434"
       environment:
         - OLLAMA_MODELS=qwen2.5:3b  # Lightweight model for testing
   ```

2. **WireMock Approach** (Faster for CI):
   ```yaml
   # docker-compose.test.yml  
   services:
     ollama-mock:
       image: wiremock/wiremock:latest
       ports:
         - "11434:8080"
       volumes:
         - ./tests/fixtures/wiremock:/home/wiremock
   ```

**Implementation Strategy:**
```python
def test_rag_query_workflow_end_to_end(client, db, ollama_test_server):
    """Test complete RAG workflow from corpus creation to query results"""
    # Real workflow: create corpus → ask question → get answer
    # Uses real RAGService, real database, mocked/test Ollama responses
    
    # TODO: Implement ollama_test_server fixture that:
    # - Uses real Ollama in local development
    # - Uses Docker container in CI
    # - Falls back to WireMock for fast CI runs
```

**Action Items for RAG Testing:**
- [ ] Create `tests/fixtures/ollama_responses.json` with sample responses
- [ ] Set up Docker container for lightweight Ollama model in CI
- [ ] Create WireMock mappings for Ollama endpoints as fallback
- [ ] Add environment detection to choose real vs mock Ollama

### 2.3 Extraction Workflow Integration Test
**File:** `tests/test_integration_extraction.py` (NEW)
**Test:** Text input → LLM extraction → database storage → GEDCOM export
```python
def test_extraction_to_gedcom_workflow(client, sample_dutch_text):
    """Test complete genealogy extraction and export workflow"""  
    # Real workflow: extract → store → export
    # Mock only Ollama API, not ExtractionTaskManager
```

### 2.4 Research Questions Integration Test
**File:** `tests/test_integration_research.py` (NEW)
**Test:** Data input → research generation → download
```python
def test_research_questions_workflow(client, sample_genealogy_data):
    """Test complete research questions generation workflow"""
    # Real workflow: process data → generate questions → download
```

## Phase 3: Refactor Over-Mocked Tests (LOW PRIORITY - ~6-8 hours)

### 3.1 Audit Current Tests
**Script:** `audit_mocking.py` (NEW)
**Purpose:** Identify tests with excessive mocking
```python
# Count mocks per test file
# Identify tests mocking internal classes
# Generate refactoring priority list
```

### 3.2 Refactor High-Priority Over-Mocked Tests
**Files to refactor first:**
- `tests/test_ocr_tasks.py` - Remove OCRTaskManager mocking
- `tests/test_extraction_tasks.py` - Remove ExtractionTaskManager mocking  
- `tests/test_rag_blueprint.py` - Remove RAGService mocking
- `tests/test_*_blueprint.py` - Remove service mocking from integration tests

**Pattern:**
```python
# BEFORE (over-mocked)
@patch('web_app.services.rag_service.RAGService')
def test_rag_query(mock_service):
    mock_service.return_value.ask_question.return_value = "mocked answer"
    
# AFTER (properly mocked)  
@patch('requests.post')  # Mock external Ollama API only
def test_rag_query(mock_ollama_api):
    mock_ollama_api.return_value.json.return_value = {"response": "real answer"}
    # Test real RAGService logic
```

### 3.3 Remove Tests Expecting Broken Behavior
**Files:** All `test_*.py`
**Find and fix:**
```python
# REMOVE these patterns:
with pytest.raises(AttributeError, match="missing attribute"):
    
# REPLACE with:
assert hasattr(obj, 'required_attribute')
```

## Phase 4: Testing Infrastructure & CI/CD (MEDIUM PRIORITY - ~3 hours)

### 4.1 Enhanced Smoke Test Infrastructure
**Goal:** Replace basic import tests with realistic traffic generation

**Requirements:**
- **Synthetic Data Generation**: Create realistic Dutch genealogy text, fake PDFs
- **Concurrent User Simulation**: Multiple workflows running simultaneously  
- **Database State Verification**: Ensure data persists correctly across workflows
- **File Handling Tests**: Real file uploads, downloads, temporary file cleanup
- **Error Recovery Testing**: Verify app doesn't crash on invalid inputs

**Implementation Files:**
```
tests/
├── smoke_tests/
│   ├── __init__.py
│   ├── traffic_generator.py      # Generate fake user workflows
│   ├── data_factories.py         # Create realistic test data
│   ├── concurrent_tester.py      # Multi-user simulation
│   └── fixtures/
│       ├── sample_dutch_text.txt
│       ├── fake_pdf_generator.py
│       └── ollama_responses.json
```

### 4.2 Ollama Test Infrastructure
**Challenge:** RAG/LLM workflows need Ollama server for real testing

**Local Development Solution:**
```python
# tests/conftest.py
@pytest.fixture
def ollama_server():
    """Use existing local Ollama installation"""
    if os.getenv('OLLAMA_HOST') == 'localhost':
        # Verify local Ollama is running
        return OllamaTestClient(real_server=True)
    else:
        return OllamaTestClient(mock_server=True)
```

**CI/CD Solutions (in priority order):**

1. **WireMock (Fastest - Recommended for most tests):**
   ```yaml
   # .github/workflows/test.yml
   services:
     ollama-mock:
       image: wiremock/wiremock:latest
       ports:
         - 11434:8080
       volumes:
         - ./tests/fixtures/wiremock:/home/wiremock/mappings
   ```

2. **Docker Ollama with Lightweight Model (For critical integration tests):**
   ```yaml
   # docker-compose.test.yml
   services:
     ollama-test:
       image: ollama/ollama:latest
       ports:
         - "11434:11434"  
       command: ["ollama", "serve"]
       healthcheck:
         test: ["CMD", "ollama", "list"]
         interval: 10s
         timeout: 5s
         retries: 3
   
   # Separate job that pulls minimal model
   - name: Setup Ollama Model
     run: |
       docker exec ollama-test ollama pull qwen2.5:3b
   ```

3. **Hybrid Approach (Best of both):**
   - WireMock for fast unit/integration tests
   - Real Docker Ollama for critical end-to-end tests
   - Environment variable controls which to use

**Action Items:**
- [ ] Create WireMock mappings for all Ollama endpoints used
- [ ] Set up Docker Ollama container with minimal model
- [ ] Add environment detection for test mode selection
- [ ] Create realistic Ollama response fixtures

## Phase 5: Test Quality Monitoring (ONGOING - ~1 hour setup)

### 4.1 Add Mock Count Limits
**File:** `pytest.ini`
**Add plugin:** `pytest-mock-count` (if available) or custom plugin
**Goal:** Warn when mock count > 50% of test assertions

### 4.2 Coverage Analysis
**Focus:** Integration coverage vs unit coverage
**Tool:** Custom script to measure:
- End-to-end workflow coverage
- External dependency mock ratios
- Real vs mocked execution paths

### 4.3 CI/CD Integration
**Update:** GitHub Actions or CI pipeline
**Add steps:**
```yaml
- name: Smoke Tests
  run: python smoke_tests.py
  
- name: Integration Tests  
  run: pytest -m integration
  
- name: Mock Audit
  run: python audit_mocking.py --fail-threshold=0.5
```

## Implementation Priority

### Session 1 (2 hours) - CRITICAL
1. ✅ Fix Celery test configuration (`conftest.py`)
2. ✅ Create first integration test (`test_integration_ocr.py`) - **No external dependencies**
3. ✅ Verify basic smoke tests + integration test pass together
4. ✅ Update `Makefile` with new test targets

### Session 2 (4 hours) - HIGH
1. ✅ **Enhanced Smoke Tests**: Create traffic generator and realistic data factories
2. ✅ **Non-LLM Integration Tests**: Create extraction and research workflow tests
3. ✅ Add pytest markers and configuration
4. ✅ Audit and mark over-mocked tests

### Session 3 (3 hours) - MEDIUM (requires Ollama setup decision)
1. ✅ **Ollama Infrastructure**: Decide on WireMock vs Docker approach for CI
2. ✅ Create RAG workflow integration tests with chosen infrastructure
3. ✅ Set up CI/CD testing pipeline with Ollama handling
4. ✅ Create WireMock mappings and/or Docker configurations

### Session 4 (4 hours) - MEDIUM  
1. ✅ Refactor highest-priority over-mocked tests
2. ✅ Remove tests expecting broken behavior
3. ✅ Add mock count monitoring and test quality metrics

### Session 5+ (ongoing) - LOW
1. ✅ Systematic refactoring of remaining tests
2. ✅ Advanced CI/CD integration features
3. ✅ Test quality monitoring and maintenance

### **IMPORTANT NOTES FOR FUTURE SESSIONS:**

**🔧 Ollama Testing Strategy Decision Needed:**
- **Option A**: WireMock only (faster CI, less realistic)
- **Option B**: Docker Ollama (slower CI, more realistic) 
- **Option C**: Hybrid approach (WireMock for most, Docker for critical tests)
- **Recommendation**: Start with WireMock, add Docker later if needed

**📊 Enhanced Smoke Tests Requirements:**
- Generate realistic Dutch genealogy text and fake PDFs
- Simulate concurrent user workflows to catch race conditions
- Test file upload/download flows with actual temporary files
- Verify error handling doesn't crash the application
- Include database state verification across workflow boundaries

## Success Metrics

### Phase 1 Success
- [ ] `pytest` runs with `CELERY_TASK_ALWAYS_EAGER = True`
- [ ] Smoke tests integrated into development workflow
- [ ] At least one real integration test exists and passes

### Phase 2 Success  
- [ ] Each major user workflow has end-to-end test
- [ ] Integration tests mock only external dependencies
- [ ] Tests would catch issues like missing `output_folder`

### Phase 3 Success
- [ ] Mock count reduced by >60% in integration tests  
- [ ] No tests expect AttributeError or broken behavior
- [ ] Real TaskManager/Service classes tested without mocking

### Overall Success
- [ ] Future bugs like OCR TaskManager issue caught by tests
- [ ] "Integration" tests actually integrate real components  
- [ ] Test failures correlate with actual broken functionality
- [ ] Developer confidence based on real verification, not false test signals

## Files to Create/Modify

### New Files
- [ ] `tests/test_integration_ocr.py`
- [ ] `tests/test_integration_rag.py` 
- [ ] `tests/test_integration_extraction.py`
- [ ] `tests/test_integration_research.py`
- [ ] `audit_mocking.py`

### Modified Files
- [ ] `tests/conftest.py` - Celery configuration
- [ ] `pytest.ini` - New markers and configuration  
- [ ] `Makefile` - New test targets
- [ ] `tests/test_ocr_tasks.py` - Remove over-mocking
- [ ] `tests/test_*_blueprint.py` - Remove service mocking
- [ ] All test files - Remove AttributeError expectations

## Rollback Plan
If reforms cause test instability:
1. Keep original test files as `test_*_original.py`
2. Git branch: `testing-reform` for iterative changes
3. Gradual rollout: One test file at a time
4. Revert specific changes, not entire reform

## Long-term Vision
- Tests that build confidence through real verification
- Integration tests that catch real integration issues  
- Unit tests for business logic, not mocked fake behavior
- Quality metrics based on working features, not test counts
- Development flow: smoke → integration → unit → deploy

---

**Next session: Start with Phase 1, Item 1.1 (Fix Celery configuration)**