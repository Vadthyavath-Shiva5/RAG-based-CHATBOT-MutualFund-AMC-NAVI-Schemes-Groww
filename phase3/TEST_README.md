# Phase 3 Integration Tests

This directory contains comprehensive test cases for Phase 3 (Indexing Layer) integration testing.

## Test Files

- `test_phase3_integration.py` - Pytest-based unit and integration tests
- `test_data.py` - Sample data and expected responses for testing
- `run_tests.py` - Simple test runner for manual testing

## Running Tests

### Option 1: Simple Test Runner
```bash
cd phase3
python run_tests.py
```

### Option 2: Test Specific Example
```bash
cd phase3
python run_tests.py --example
```

### Option 3: Pytest (requires pytest installation)
```bash
pip install pytest
cd phase3
pytest test_phase3_integration.py -v
```

## Test Cases Covered

### 1. Configuration Tests
- ✅ Config loading from `.env`
- ✅ API key validation
- ✅ Provider/model settings

### 2. Component Tests
- ✅ Embedding model initialization (OpenAI)
- ✅ Vector store operations (FAISS)
- ✅ Document store operations (SQLite)
- ✅ Typed facts extraction

### 3. Retrieval Tests
- ✅ Query classification (numeric/educational/factual)
- ✅ Numeric query retrieval (typed facts)
- ✅ Educational query retrieval (AMFI/SEBI priority)
- ✅ Factual query retrieval (vector search)

### 4. Integration Test Cases

| Query | Expected Answer | Source URL | Type |
|-------|----------------|------------|------|
| "what is the AUM of Navi AMC?" | INR 9,102.56 Cr | groww.in/mutual-funds/amc/navi-mutual-funds | Numeric |
| "what is NAV?" | NAV explanation | amfiindia.com/nav | Educational |
| "what is the minimum SIP for Navi Flexi Cap?" | INR 100 | groww.in/navi-flexi-cap | Numeric |
| "what is expense ratio?" | Expense ratio explanation | amfiindia.com/expense-ratio | Educational |
| "tell me about Navi mutual funds" | AMC overview | groww.in/navi-mutual-funds | Factual |
| "what is the lock-in period for ELSS?" | 3 years | groww.in/navi-elss-tax-saver | Numeric |

## Example Test Output

```
🎯 Testing Specific Example: AUM Query
========================================
Query: what is the AUM of Navi AMC?

📋 Retrieval Results:
1. [typed_fact] AUM: INR 9,102.56 Cr
   URL: https://groww.in/mutual-funds/amc/navi-mutual-funds

📊 Validation:
   Answer found: ✅
   URL found: ✅

🎉 Example test PASSED!
```

## Test Data

The tests use realistic sample data including:
- Navi AMC overview with AUM facts
- Scheme details (Flexi Cap, ELSS, Large Midcap)
- AMFI educational content (NAV, expense ratio)
- Typed facts extraction for numeric queries

## Dependencies

Tests require:
- `openai` - For API access
- `faiss-cpu` - For vector operations
- `numpy` - For numerical computations
- `pytest` - For running pytest tests (optional)

## Mock Testing

If OpenAI API is not available, the tests will automatically fall back to mock implementations for development testing.

## LLM Integration Testing

For full LLM integration testing (generating natural language responses), ensure:
1. OpenAI API key is configured in `.env`
2. API has sufficient credits
3. Network connectivity to OpenAI services

## Troubleshooting

### Common Issues

1. **API Key Not Found**: Ensure `.env` file exists with correct API keys
2. **OpenAI API Errors**: Check API key validity and credits
3. **Import Errors**: Install required dependencies with `pip install -r requirements.txt`
4. **Database Errors**: Delete test database files (`data/test_doc.db`) and re-run

### Debug Mode

Set `API_DEBUG=true` in `.env` for verbose logging during tests.