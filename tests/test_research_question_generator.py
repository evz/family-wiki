"""
Tests for research question generator functionality
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import requests

from web_app.research_question_generator import ResearchQuestion, ResearchQuestionGenerator


class TestResearchQuestion:
    """Test ResearchQuestion dataclass"""

    def test_research_question_creation(self):
        """Test creating a research question"""
        question = ResearchQuestion(
            category="Test Category",
            question="Test question?",
            evidence="Test evidence",
            priority="high",
            research_type="archival",
            difficulty="moderate",
            potential_sources=["Source 1", "Source 2"]
        )

        assert question.category == "Test Category"
        assert question.question == "Test question?"
        assert question.evidence == "Test evidence"
        assert question.priority == "high"
        assert question.research_type == "archival"
        assert question.difficulty == "moderate"
        assert question.potential_sources == ["Source 1", "Source 2"]


class TestResearchQuestionGenerator:
    """Test research question generator functionality"""

    def test_initialization_default(self):
        """Test default initialization"""
        generator = ResearchQuestionGenerator()

        assert generator.text_file == Path("pdf_processing/extracted_text/consolidated_text.txt")
        assert generator.llm_results_file == Path("llm_genealogy_results.json")
        assert generator.text_content == ""
        assert generator.people_data == []
        assert generator.research_questions == []

        # Check historical periods
        assert 'napoleonic' in generator.historical_periods
        assert 'wwii' in generator.historical_periods
        assert generator.historical_periods['napoleonic'] == (1795, 1815)
        assert generator.historical_periods['wwii'] == (1940, 1945)

    def test_initialization_custom_params(self):
        """Test initialization with custom parameters"""
        generator = ResearchQuestionGenerator(
            text_file="custom_text.txt",
            llm_results="custom_results.json"
        )

        assert generator.text_file == Path("custom_text.txt")
        assert generator.llm_results_file == Path("custom_results.json")

    def test_historical_periods_data(self):
        """Test historical periods configuration"""
        generator = ResearchQuestionGenerator()

        expected_periods = {
            'napoleonic': (1795, 1815),
            'golden_age': (1588, 1672),
            'wwi': (1914, 1918),
            'wwii': (1940, 1945),
            'great_depression': (1929, 1939),
            'industrial_revolution': (1850, 1900)
        }

        assert generator.historical_periods == expected_periods

    def test_dutch_regions_data(self):
        """Test Dutch regions configuration"""
        generator = ResearchQuestionGenerator()

        expected_regions = {
            'groningen', 'friesland', 'drenthe', 'overijssel', 'gelderland',
            'utrecht', 'noord-holland', 'zuid-holland', 'zeeland', 'noord-brabant',
            'limburg', 'flevoland'
        }

        assert generator.dutch_regions == expected_regions

    def test_major_dutch_cities_data(self):
        """Test major Dutch cities configuration"""
        generator = ResearchQuestionGenerator()

        # Check a few key cities
        assert 'amsterdam' in generator.major_dutch_cities
        assert 'rotterdam' in generator.major_dutch_cities
        assert 'utrecht' in generator.major_dutch_cities
        assert 'groningen' in generator.major_dutch_cities
        assert 'culemborg' in generator.major_dutch_cities  # From the genealogy context

    def test_load_data_text_only(self):
        """Test loading text data only"""
        generator = ResearchQuestionGenerator()

        # Create temporary text file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("Test genealogy text with names and dates 1800-1900")
            text_file = f.name

        try:
            generator.text_file = Path(text_file)
            generator.load_data()

            assert generator.text_content == "Test genealogy text with names and dates 1800-1900"
            assert generator.people_data == []
        finally:
            Path(text_file).unlink()

    def test_load_data_llm_results_only(self):
        """Test loading LLM results only"""
        generator = ResearchQuestionGenerator()

        # Create temporary LLM results file
        test_data = {
            "people": [
                {"given_names": "Jan", "surname": "Jansen", "birth_date": "1800"},
                {"given_names": "Piet", "surname": "Pietersen", "birth_date": "1825"}
            ]
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(test_data, f)
            results_file = f.name

        try:
            generator.llm_results_file = Path(results_file)
            generator.load_data()

            assert generator.text_content == ""
            assert len(generator.people_data) == 2
            assert generator.people_data[0]["given_names"] == "Jan"
        finally:
            Path(results_file).unlink()

    def test_load_data_both_files(self):
        """Test loading both text and LLM results"""
        generator = ResearchQuestionGenerator()

        # Create temporary text file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("Test genealogy text")
            text_file = f.name

        # Create temporary LLM results file
        test_data = {"people": [{"given_names": "Jan", "surname": "Jansen"}]}
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(test_data, f)
            results_file = f.name

        try:
            generator.text_file = Path(text_file)
            generator.llm_results_file = Path(results_file)
            generator.load_data()

            assert generator.text_content == "Test genealogy text"
            assert len(generator.people_data) == 1
            assert generator.people_data[0]["given_names"] == "Jan"
        finally:
            Path(text_file).unlink()
            Path(results_file).unlink()

    def test_load_data_no_files(self):
        """Test loading data when no files exist"""
        generator = ResearchQuestionGenerator()
        generator.text_file = Path("nonexistent.txt")
        generator.llm_results_file = Path("nonexistent.json")

        # Should not raise exception
        generator.load_data()

        assert generator.text_content == ""
        assert generator.people_data == []

    def test_analyze_missing_information_gaps_no_data(self):
        """Test analyzing missing information when no people data available"""
        generator = ResearchQuestionGenerator()

        questions = generator.analyze_missing_information_gaps()

        assert questions == []

    def test_analyze_missing_information_gaps_with_data(self):
        """Test analyzing missing information with actual data"""
        generator = ResearchQuestionGenerator()

        # Set up test data with missing information
        generator.people_data = [
            {"given_names": "Jan", "surname": "Jansen", "birth_date": "1800"},  # Has birth
            {"given_names": "Piet", "surname": "Pietersen"},  # Missing birth and death
            {"given_names": "Klaas", "surname": "Klaassen", "death_date": "1900"}  # Missing birth, has death
        ]

        questions = generator.analyze_missing_information_gaps()

        assert len(questions) > 0

        # Check for birth information questions
        birth_questions = [q for q in questions if "birth" in q.question.lower()]
        assert len(birth_questions) > 0

        birth_question = birth_questions[0]
        assert birth_question.category == "Missing Vital Records"
        assert birth_question.priority == "high"
        assert birth_question.research_type == "archival"
        assert "Birth registers" in birth_question.potential_sources

    def test_analyze_missing_information_gaps_deaths(self):
        """Test analyzing missing death information"""
        generator = ResearchQuestionGenerator()

        generator.people_data = [
            {"given_names": "Jan", "surname": "Jansen", "birth_date": "1800"},  # Missing death
            {"given_names": "Piet", "surname": "Pietersen", "birth_date": "1825"}  # Missing death
        ]

        questions = generator.analyze_missing_information_gaps()

        death_questions = [q for q in questions if "death" in q.question.lower()]
        assert len(death_questions) > 0

        death_question = death_questions[0]
        assert death_question.category == "Missing Vital Records"
        assert death_question.priority == "medium"
        assert "Death registers" in death_question.potential_sources

    def test_analyze_geographic_patterns_no_text(self):
        """Test geographic analysis with no text"""
        generator = ResearchQuestionGenerator()

        questions = generator.analyze_geographic_patterns()

        assert questions == []

    def test_analyze_geographic_patterns_with_places(self):
        """Test geographic analysis with place names"""
        generator = ResearchQuestionGenerator()

        # Text with Dutch place names
        generator.text_content = "Jan Jansen was born in Amsterdam and later moved to Rotterdam. The family also had connections to Utrecht and Groningen. Amsterdam was mentioned frequently in the records."

        questions = generator.analyze_geographic_patterns()

        assert len(questions) > 0

        # Check for geographic migration questions
        migration_questions = [q for q in questions if q.category == "Geographic Migration"]
        assert len(migration_questions) > 0

        question = migration_questions[0]
        assert "Amsterdam" in question.evidence or "Rotterdam" in question.evidence
        assert question.research_type == "online"

    def test_analyze_geographic_patterns_multiple_locations(self):
        """Test geographic analysis with multiple locations"""
        generator = ResearchQuestionGenerator()

        # Text with many different locations
        generator.text_content = """
        The family lived in Amsterdam, Rotterdam, Utrecht, Groningen, and Eindhoven.
        They moved from Amsterdam to Rotterdam in 1800, then to Utrecht in 1825.
        Some family members remained in Groningen while others went to Eindhoven.
        """

        questions = generator.analyze_geographic_patterns()

        # Should generate questions about migration patterns
        migration_questions = [q for q in questions if "migration" in q.question.lower()]
        assert len(migration_questions) > 0

        question = migration_questions[0]
        assert "multiple locations" in question.evidence.lower()

    def test_analyze_occupational_patterns_no_occupations(self):
        """Test occupational analysis with no occupations"""
        generator = ResearchQuestionGenerator()
        generator.text_content = "Jan Jansen was born in 1800 and died in 1870."

        questions = generator.analyze_occupational_patterns()

        assert questions == []

    def test_analyze_occupational_patterns_with_occupations(self):
        """Test occupational analysis with occupations"""
        generator = ResearchQuestionGenerator()

        generator.text_content = "Jan Jansen was a bakker (baker) in Amsterdam. His son Piet was an arbeider (worker) in Rotterdam. The family also included a koopman (merchant)."

        questions = generator.analyze_occupational_patterns()

        assert len(questions) > 0

        # Check for occupational questions
        occ_questions = [q for q in questions if q.category == "Social and Economic History"]
        assert len(occ_questions) > 0

        question = occ_questions[0]
        assert "bakker" in question.evidence.lower() or "arbeider" in question.evidence.lower()
        assert "Guild records" in question.potential_sources

    def test_analyze_occupational_patterns_laborers(self):
        """Test occupational analysis with laborers"""
        generator = ResearchQuestionGenerator()

        generator.text_content = "Jan was an arbeider. Piet was also an arbeider. Many family members were listed as arbeider or worker."

        questions = generator.analyze_occupational_patterns()

        # Should generate industrial history questions
        industrial_questions = [q for q in questions if q.category == "Industrial History"]
        assert len(industrial_questions) > 0

        question = industrial_questions[0]
        assert "arbeider" in question.evidence.lower()
        assert question.priority == "low"

    def test_analyze_naming_patterns_no_data(self):
        """Test naming pattern analysis with no data"""
        generator = ResearchQuestionGenerator()

        questions = generator.analyze_naming_patterns()

        assert questions == []

    def test_analyze_naming_patterns_surname_variations(self):
        """Test naming pattern analysis with surname variations"""
        generator = ResearchQuestionGenerator()

        generator.people_data = [
            {"given_names": "Jan", "surname": "van Zanten"},
            {"given_names": "Piet", "surname": "van Santen"},
            {"given_names": "Klaas", "surname": "van Zanten"}
        ]

        questions = generator.analyze_naming_patterns()

        # Should generate questions about name variations
        name_questions = [q for q in questions if q.category == "Name Variations"]
        assert len(name_questions) > 0

        question = name_questions[0]
        assert "van Zanten" in question.evidence and "van Santen" in question.evidence
        assert question.priority == "high"

    def test_analyze_naming_patterns_given_names(self):
        """Test naming pattern analysis with repeated given names"""
        generator = ResearchQuestionGenerator()

        generator.people_data = [
            {"given_names": "Jan Pieter", "surname": "Jansen"},
            {"given_names": "Jan", "surname": "Pietersen"},
            {"given_names": "Pieter", "surname": "Klaassen"},
            {"given_names": "Jan Willem", "surname": "Henriksen"}
        ]

        questions = generator.analyze_naming_patterns()

        # Should generate questions about naming traditions
        tradition_questions = [q for q in questions if q.category == "Naming Traditions"]
        assert len(tradition_questions) > 0

        question = tradition_questions[0]
        assert "Jan" in question.evidence  # Jan appears 3 times

    def test_analyze_historical_context_no_years(self):
        """Test historical context analysis with no years"""
        generator = ResearchQuestionGenerator()
        generator.text_content = "Jan Jansen was born and died."

        questions = generator.analyze_historical_context()

        assert questions == []

    def test_analyze_historical_context_napoleonic_period(self):
        """Test historical context analysis for Napoleonic period"""
        generator = ResearchQuestionGenerator()
        generator.text_content = "Jan Jansen was born in 1800 and died in 1870. The family records span from 1795 to 1850."

        questions = generator.analyze_historical_context()

        # Should generate Napoleonic period questions
        napoleonic_questions = [q for q in questions if "napoleonic" in q.question.lower()]
        assert len(napoleonic_questions) > 0

        question = napoleonic_questions[0]
        assert question.category == "Historical Context"
        assert "1795-1815" in question.question

    def test_analyze_historical_context_wwii_period(self):
        """Test historical context analysis for WWII period"""
        generator = ResearchQuestionGenerator()
        generator.text_content = "The family lived from 1920 to 1950, experiencing both world wars."

        questions = generator.analyze_historical_context()

        # Should generate WWII questions
        wwii_questions = [q for q in questions if "world war ii" in q.question.lower()]
        assert len(wwii_questions) > 0

        question = wwii_questions[0]
        assert question.category == "20th Century History"
        assert question.priority == "high"

    def test_analyze_religious_context_no_terms(self):
        """Test religious context analysis with no religious terms"""
        generator = ResearchQuestionGenerator()
        generator.text_content = "Jan Jansen was born in 1800."

        questions = generator.analyze_religious_context()

        assert questions == []

    def test_analyze_religious_context_with_terms(self):
        """Test religious context analysis with religious terms"""
        generator = ResearchQuestionGenerator()
        generator.text_content = "Jan Jansen was gedoopt (baptized) in the gereformeerde kerk (reformed church). The family was hervormd (protestant)."

        questions = generator.analyze_religious_context()

        assert len(questions) > 0

        # Check for religious questions
        religious_questions = [q for q in questions if q.category == "Religious History"]
        assert len(religious_questions) > 0

        question = religious_questions[0]
        assert "gereformeerde" in question.evidence.lower() or "hervormd" in question.evidence.lower()
        assert question.research_type == "archival"

    @patch('requests.post')
    def test_query_llm_for_insights_success(self, mock_post):
        """Test successful LLM query for insights"""
        generator = ResearchQuestionGenerator()

        # Mock LLM response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'response': '''[
                {
                    "question": "What was the family's involvement in local guilds?",
                    "rationale": "Multiple family members had trade occupations",
                    "research_type": "archival",
                    "difficulty": "moderate"
                }
            ]'''
        }
        mock_post.return_value = mock_response

        questions = generator.query_llm_for_insights("Test genealogy text")

        assert len(questions) == 1
        assert questions[0].category == "AI-Generated Insights"
        assert "guild" in questions[0].question.lower()
        assert questions[0].research_type == "archival"
        assert questions[0].difficulty == "moderate"

    @patch('requests.post')
    def test_query_llm_for_insights_no_json(self, mock_post):
        """Test LLM query with no JSON response"""
        generator = ResearchQuestionGenerator()

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'response': 'This is not JSON format'
        }
        mock_post.return_value = mock_response

        questions = generator.query_llm_for_insights("Test text")

        assert questions == []

    @patch('requests.post')
    def test_query_llm_for_insights_invalid_json(self, mock_post):
        """Test LLM query with invalid JSON response"""
        generator = ResearchQuestionGenerator()

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'response': '[{"question": "test", invalid json}'
        }
        mock_post.return_value = mock_response

        questions = generator.query_llm_for_insights("Test text")

        assert questions == []

    @patch('requests.post')
    def test_query_llm_for_insights_request_failure(self, mock_post):
        """Test LLM query with request failure"""
        generator = ResearchQuestionGenerator()

        mock_post.side_effect = requests.exceptions.RequestException("Connection failed")

        questions = generator.query_llm_for_insights("Test text")

        assert questions == []

    @patch('requests.post')
    def test_query_llm_for_insights_http_error(self, mock_post):
        """Test LLM query with HTTP error"""
        generator = ResearchQuestionGenerator()

        mock_response = Mock()
        mock_response.status_code = 500
        mock_post.return_value = mock_response

        questions = generator.query_llm_for_insights("Test text")

        assert questions == []

    def test_generate_all_questions_no_data(self):
        """Test generating all questions with no data"""
        generator = ResearchQuestionGenerator()

        # Mock all analysis methods to return empty lists
        with patch.object(generator, 'load_data'), \
             patch.object(generator, 'analyze_missing_information_gaps', return_value=[]), \
             patch.object(generator, 'analyze_geographic_patterns', return_value=[]), \
             patch.object(generator, 'analyze_occupational_patterns', return_value=[]), \
             patch.object(generator, 'analyze_naming_patterns', return_value=[]), \
             patch.object(generator, 'analyze_historical_context', return_value=[]), \
             patch.object(generator, 'analyze_religious_context', return_value=[]), \
             patch.object(generator, 'query_llm_for_insights', return_value=[]):

            generator.generate_all_questions()

            assert generator.research_questions == []

    def test_generate_all_questions_with_data(self):
        """Test generating all questions with mock data"""
        generator = ResearchQuestionGenerator()

        # Mock some sample questions
        sample_questions = [
            ResearchQuestion("Test", "Test question?", "Test evidence", "high", "archival", "moderate", ["Source 1"]),
            ResearchQuestion("Test 2", "Test question 2?", "Test evidence 2", "medium", "online", "easy", ["Source 2"])
        ]

        with patch.object(generator, 'load_data'), \
             patch.object(generator, 'analyze_missing_information_gaps', return_value=sample_questions[:1]), \
             patch.object(generator, 'analyze_geographic_patterns', return_value=sample_questions[1:]), \
             patch.object(generator, 'analyze_occupational_patterns', return_value=[]), \
             patch.object(generator, 'analyze_naming_patterns', return_value=[]), \
             patch.object(generator, 'analyze_historical_context', return_value=[]), \
             patch.object(generator, 'analyze_religious_context', return_value=[]), \
             patch.object(generator, 'query_llm_for_insights', return_value=[]):

            generator.generate_all_questions()

            assert len(generator.research_questions) == 2
            assert generator.research_questions[0].category == "Test"
            assert generator.research_questions[1].category == "Test 2"

    def test_generate_all_questions_with_text_content(self):
        """Test generating all questions with text content for LLM"""
        generator = ResearchQuestionGenerator()
        generator.text_content = "This is a long text content that should be processed by LLM for additional insights."

        with patch.object(generator, 'load_data'), \
             patch.object(generator, 'analyze_missing_information_gaps', return_value=[]), \
             patch.object(generator, 'analyze_geographic_patterns', return_value=[]), \
             patch.object(generator, 'analyze_occupational_patterns', return_value=[]), \
             patch.object(generator, 'analyze_naming_patterns', return_value=[]), \
             patch.object(generator, 'analyze_historical_context', return_value=[]), \
             patch.object(generator, 'analyze_religious_context', return_value=[]), \
             patch.object(generator, 'query_llm_for_insights', return_value=[]) as mock_llm:

            generator.generate_all_questions()

            # Should call LLM with text sample
            mock_llm.assert_called_once()
            call_args = mock_llm.call_args[0]
            assert len(call_args[0]) <= 2000  # Should be a sample of text

    def test_prioritize_questions(self):
        """Test question prioritization"""
        generator = ResearchQuestionGenerator()

        # Create questions with different priorities and difficulties
        generator.research_questions = [
            ResearchQuestion("Test", "Low priority easy", "Evidence", "low", "online", "easy", ["Source 1"]),
            ResearchQuestion("Test", "High priority difficult", "Evidence", "high", "archival", "difficult", ["Source 2"]),
            ResearchQuestion("Test", "Medium priority moderate", "Evidence", "medium", "online", "moderate", ["Source 3"]),
            ResearchQuestion("Test", "High priority easy", "Evidence", "high", "online", "easy", ["Source 4"])
        ]

        generator.prioritize_questions()

        # Should be sorted by priority + difficulty score (highest first)
        # high(3) + easy(3) = 6
        # high(3) + difficult(1) = 4
        # medium(2) + moderate(2) = 4
        # low(1) + easy(3) = 4

        assert generator.research_questions[0].question == "High priority easy"  # Score: 6

        # The next three all have score 4, so they could be in any order
        # Let's just check that the first one is correct and the rest are the remaining ones
        remaining_questions = [q.question for q in generator.research_questions[1:]]
        expected_remaining = ["High priority difficult", "Medium priority moderate", "Low priority easy"]

        assert len(remaining_questions) == 3
        assert all(q in expected_remaining for q in remaining_questions)

    def test_save_questions(self):
        """Test saving questions to file"""
        generator = ResearchQuestionGenerator()

        # Create sample questions
        generator.research_questions = [
            ResearchQuestion("Test Category", "Test question?", "Test evidence", "high", "archival", "moderate", ["Source 1", "Source 2"])
        ]

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            output_file = f.name

        try:
            generator.save_questions(output_file)

            # Verify file was created and contains correct data
            with open(output_file) as f:
                saved_data = json.load(f)

            assert 'metadata' in saved_data
            assert 'questions' in saved_data
            assert saved_data['metadata']['total_questions'] == 1
            assert saved_data['metadata']['categories'] == ['Test Category']

            question = saved_data['questions'][0]
            assert question['category'] == 'Test Category'
            assert question['question'] == 'Test question?'
            assert question['evidence'] == 'Test evidence'
            assert question['priority'] == 'high'
            assert question['research_type'] == 'archival'
            assert question['difficulty'] == 'moderate'
            assert question['potential_sources'] == ['Source 1', 'Source 2']

        finally:
            Path(output_file).unlink()

    def test_save_questions_empty(self):
        """Test saving empty questions"""
        generator = ResearchQuestionGenerator()

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            output_file = f.name

        try:
            generator.save_questions(output_file)

            # Verify file was created and contains empty data
            with open(output_file) as f:
                saved_data = json.load(f)

            assert saved_data['metadata']['total_questions'] == 0
            assert saved_data['questions'] == []

        finally:
            Path(output_file).unlink()

    def test_print_summary_no_questions(self):
        """Test printing summary with no questions"""
        generator = ResearchQuestionGenerator()

        # Should not raise exception
        generator.print_summary()

    def test_print_summary_with_questions(self):
        """Test printing summary with questions"""
        generator = ResearchQuestionGenerator()

        # Create sample questions
        generator.research_questions = [
            ResearchQuestion("Missing Records", "What birth dates are missing?", "Evidence 1", "high", "archival", "moderate", ["Source 1"]),
            ResearchQuestion("Missing Records", "What death dates are missing?", "Evidence 2", "medium", "archival", "easy", ["Source 2"]),
            ResearchQuestion("Geographic", "Migration patterns?", "Evidence 3", "low", "online", "difficult", ["Source 3"])
        ]

        # Should not raise exception
        generator.print_summary()

    @patch('web_app.research_question_generator.ResearchQuestionGenerator')
    def test_main_function(self, mock_generator_class):
        """Test main function"""
        mock_generator = Mock()
        mock_generator_class.return_value = mock_generator

        # Import and call main
        from web_app.research_question_generator import main
        main()

        mock_generator.generate_all_questions.assert_called_once()
        mock_generator.prioritize_questions.assert_called_once()
        mock_generator.print_summary.assert_called_once()
        mock_generator.save_questions.assert_called_once()
