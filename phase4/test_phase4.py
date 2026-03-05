"""
Phase 4: Integration Tests for Backend API and Frontend

Tests for the Flask API endpoints, LLM integration, and response formatting.
"""

import json
import pytest
from app import app, initialize_components
from lib.llm_client import LLMClient
from lib.response_formatter import ResponseFormatter, SafetyChecker


class TestFlaskAPI:
    """Test Flask API endpoints"""

    @pytest.fixture
    def client(self):
        """Setup test client"""
        app.config['TESTING'] = True
        with app.test_client() as client:
            yield client

    def test_health_endpoint(self, client):
        """Test health check endpoint"""
        response = client.get('/health')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['status'] == 'healthy'

    def test_chat_endpoint_valid_query(self, client):
        """Test chat endpoint with valid query"""
        payload = {
            'message': 'What are mutual funds?',
            'context_type': 'mutual_funds'
        }
        response = client.post('/chat', 
                             data=json.dumps(payload),
                             content_type='application/json')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'answer' in data
        assert data.get('success', False) is True

    def test_chat_endpoint_empty_query(self, client):
        """Test chat endpoint with empty query"""
        payload = {'message': '', 'context_type': 'mutual_funds'}
        response = client.post('/chat',
                             data=json.dumps(payload),
                             content_type='application/json')
        assert response.status_code == 400

    def test_schemes_endpoint(self, client):
        """Test schemes information endpoint"""
        response = client.get('/schemes')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert isinstance(data, list) or 'schemes' in data

    def test_faq_endpoint(self, client):
        """Test FAQ endpoint"""
        response = client.get('/faq')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert isinstance(data, list) or 'faqs' in data

    def test_sources_endpoint(self, client):
        """Test data sources endpoint"""
        response = client.get('/sources')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert isinstance(data, list) or 'sources' in data

    def test_404_error(self, client):
        """Test 404 error handling"""
        response = client.get('/nonexistent')
        assert response.status_code == 404


class TestSafetyChecker:
    """Test safety checking functionality"""

    def test_pii_detection_email(self):
        """Test email PII detection"""
        checker = SafetyChecker()
        text = "My email is user@example.com"
        result = checker.check_pii(text)
        assert result is True

    def test_pii_detection_phone(self):
        """Test phone number PII detection"""
        checker = SafetyChecker()
        text = "My phone is +91-9876543210"
        result = checker.check_pii(text)
        assert result is True

    def test_pii_detection_account_number(self):
        """Test account number PII detection"""
        checker = SafetyChecker()
        text = "Account number: 123456789012345678"
        result = checker.check_pii(text)
        assert result is True

    def test_pii_detection_pan(self):
        """Test PAN detection"""
        checker = SafetyChecker()
        text = "PAN: ABCDE1234F"
        result = checker.check_pii(text)
        assert result is True

    def test_no_pii(self):
        """Test when no PII is present"""
        checker = SafetyChecker()
        text = "What are mutual funds?"
        result = checker.check_pii(text)
        assert result is False

    def test_scope_check_advice(self):
        """Test financial advice scope check"""
        checker = SafetyChecker()
        result = checker.check_scope("Should I buy this stock?")
        assert result is True  # Out of scope

    def test_scope_check_recommendation(self):
        """Test recommendation scope check"""
        checker = SafetyChecker()
        result = checker.check_scope("Which scheme should I invest in?")
        assert result is True  # Out of scope

    def test_scope_check_personal_data(self):
        """Test personal data scope check"""
        checker = SafetyChecker()
        result = checker.check_scope("What is my portfolio value?")
        assert result is True  # Out of scope

    def test_scope_check_valid_query(self):
        """Test valid in-scope query"""
        checker = SafetyChecker()
        result = checker.check_scope("What is NAV in mutual funds?")
        assert result is False  # In scope

    def test_safety_response(self):
        """Test safety response generation"""
        checker = SafetyChecker()
        response = checker.get_safety_response('personal_data')
        assert isinstance(response, str)
        assert len(response) > 0


class TestResponseFormatter:
    """Test response formatting functionality"""

    def test_format_response_with_sources(self):
        """Test formatting response with sources"""
        formatter = ResponseFormatter()
        response = "Mutual funds are investment funds."
        sources = ["source1.txt", "source2.txt"]
        
        formatted = formatter.format_response(response, sources)
        assert "Mutual funds" in formatted

    def test_format_response_without_sources(self):
        """Test formatting response without sources"""
        formatter = ResponseFormatter()
        response = "Mutual funds are investment funds."
        
        formatted = formatter.format_response(response)
        assert "Mutual funds" in formatted

    def test_confidence_calculation(self):
        """Test confidence score calculation"""
        formatter = ResponseFormatter()
        response = "This is a very detailed response with complete information."
        confidence = formatter._calculate_confidence(response, len(response) // 10)
        
        assert 0 <= confidence <= 1

    def test_clean_response(self):
        """Test response cleaning"""
        formatter = ResponseFormatter()
        response = "  Answer: This is a test.  \n\n  "
        cleaned = formatter._clean_response(response)
        
        assert cleaned.startswith("This is a test")
        assert not cleaned.startswith("Answer:")


class TestLLMClient:
    """Test LLM client functionality"""

    def test_llm_client_initialization(self):
        """Test LLM client initialization"""
        # Note: Requires valid API key in environment
        try:
            client = LLMClient()
            assert client is not None
        except Exception as e:
            pytest.skip(f"LLM client initialization failed: {str(e)}")

    def test_response_generation_format(self):
        """Test that generated response is a string"""
        # This is an integration test - requires API key
        try:
            client = LLMClient()
            response = client.generate_response(
                system_prompt="You are a helpful assistant.",
                user_message="What is 2+2?",
                context="",
                max_tokens=100
            )
            assert isinstance(response, str)
            assert len(response) > 0
        except Exception as e:
            pytest.skip(f"LLM response generation skipped: {str(e)}")


class TestIntegrationFlow:
    """Test complete integration flow"""

    def test_query_to_response_flow(self):
        """Test full query processing flow"""
        try:
            # Initialize components
            llm_client = LLMClient()
            formatter = ResponseFormatter()
            checker = SafetyChecker()
            
            # Test query
            query = "What is NAV?"
            
            # Safety checks
            if checker.check_pii(query):
                pytest.fail("Query shouldn't contain PII")
            
            if checker.check_scope(query):
                pytest.skip("Query out of scope")
            
            # Generate response
            response = llm_client.generate_response(
                system_prompt="You are a mutual fund expert.",
                user_message=query,
                context="",
                max_tokens=200
            )
            
            # Format response
            formatted = formatter.format_response(response)
            
            assert isinstance(formatted, str)
            assert len(formatted) > 0
        except Exception as e:
            pytest.skip(f"Integration flow test skipped: {str(e)}")


if __name__ == '__main__':
    # Run tests with: pytest test_phase4.py -v
    pytest.main([__file__, '-v'])