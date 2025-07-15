"""
Intelligent research question generator for genealogical analysis
"""

import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path

import requests
from flask import current_app

from web_app.shared.logging_config import get_project_logger


logger = get_project_logger(__name__)

@dataclass
class ResearchQuestion:
    category: str
    question: str
    evidence: str
    priority: str  # high, medium, low
    research_type: str  # archival, online, dna, local_records
    difficulty: str  # easy, moderate, difficult
    potential_sources: list[str]

class ResearchQuestionGenerator:
    def __init__(self, text_file: str = None, llm_results: str = None):
        # Use Flask config for defaults
        self.text_file = Path(text_file or "pdf_processing/extracted_text/consolidated_text.txt")
        self.llm_results_file = Path(llm_results or "llm_genealogy_results.json")
        self.text_content = ""
        self.people_data = []
        self.research_questions = []

        # Historical context patterns
        self.historical_periods = {
            'napoleonic': (1795, 1815),
            'golden_age': (1588, 1672),
            'wwi': (1914, 1918),
            'wwii': (1940, 1945),
            'great_depression': (1929, 1939),
            'industrial_revolution': (1850, 1900)
        }

        # Dutch regional knowledge
        self.dutch_regions = {
            'groningen', 'friesland', 'drenthe', 'overijssel', 'gelderland',
            'utrecht', 'noord-holland', 'zuid-holland', 'zeeland', 'noord-brabant',
            'limburg', 'flevoland'
        }

        self.major_dutch_cities = {
            'amsterdam', 'rotterdam', 'den haag', 'utrecht', 'eindhoven',
            'tilburg', 'groningen', 'almere', 'breda', 'nijmegen', 'enschede',
            'haarlem', 'arnhem', 'amersfoort', 'zaanstad', 'haarlemmermeer',
            'culemborg', 'zuilichem', 'gameren', 'haaften', 'gorinchem', 'deil'
        }

    def load_data(self) -> None:
        """Load both raw text and structured data"""
        # Load raw text
        if self.text_file.exists():
            with open(self.text_file, encoding='utf-8') as f:
                self.text_content = f.read()
            logger.info(f"Loaded text content: {len(self.text_content)} characters")

        # Load LLM results if available
        if self.llm_results_file.exists():
            with open(self.llm_results_file, encoding='utf-8') as f:
                data = json.load(f)
                self.people_data = data.get('people', [])
            logger.info(f"Loaded {len(self.people_data)} people from LLM results")

    def analyze_missing_information_gaps(self) -> list[ResearchQuestion]:
        """Identify missing information that could be researched"""
        questions = []

        if not self.people_data:
            return questions

        # Analyze completeness of data
        missing_births = [p for p in self.people_data if not p.get('birth_date')]
        missing_deaths = [p for p in self.people_data if not p.get('death_date')]
        # Note: these were unused variables - removed to fix linting
        # missing_marriages = [p for p in self.people_data if not p.get('spouse_name') and not p.get('marriage_date')]
        # missing_places = [p for p in self.people_data if not p.get('birth_place') and not p.get('baptism_place')]

        if missing_births:
            sample_names = [f"{p.get('given_names', '')} {p.get('surname', '')}" for p in missing_births[:3]]
            questions.append(ResearchQuestion(
                category="Missing Vital Records",
                question=f"What are the birth dates and places for {len(missing_births)} individuals with incomplete birth information?",
                evidence=f"Examples: {', '.join(sample_names)}",
                priority="high",
                research_type="archival",
                difficulty="moderate",
                potential_sources=["Birth registers", "Baptism records", "Church books", "Civil registration"]
            ))

        if missing_deaths:
            sample_names = [f"{p.get('given_names', '')} {p.get('surname', '')}" for p in missing_deaths[:3]]
            questions.append(ResearchQuestion(
                category="Missing Vital Records",
                question=f"What are the death dates and circumstances for {len(missing_deaths)} individuals?",
                evidence=f"Examples: {', '.join(sample_names)}",
                priority="medium",
                research_type="archival",
                difficulty="moderate",
                potential_sources=["Death registers", "Burial records", "Cemetery records", "Obituaries"]
            ))

        return questions

    def analyze_geographic_patterns(self) -> list[ResearchQuestion]:
        """Analyze geographic distribution and migration patterns"""
        questions = []

        # Extract places mentioned in text
        place_pattern = r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b'
        places_in_text = re.findall(place_pattern, self.text_content)

        # Count place mentions
        place_counts = Counter(places_in_text)
        frequent_places = [place for place, count in place_counts.most_common(10)
                          if place.lower() in self.major_dutch_cities or count > 5]

        if frequent_places:
            questions.append(ResearchQuestion(
                category="Geographic Migration",
                question="What caused the family concentration in specific Dutch regions?",
                evidence=f"Frequent locations: {', '.join(frequent_places[:5])}",
                priority="medium",
                research_type="online",
                difficulty="easy",
                potential_sources=["Regional histories", "Economic records", "Migration databases", "Maps"]
            ))

        # Look for migration patterns
        if len(set(frequent_places)) > 3:
            questions.append(ResearchQuestion(
                category="Geographic Migration",
                question="What migration routes did the family follow and why?",
                evidence=f"Family present in multiple locations: {', '.join(frequent_places)}",
                priority="medium",
                research_type="online",
                difficulty="moderate",
                potential_sources=["Migration records", "Economic history", "Transportation history", "Regional archives"]
            ))

        return questions

    def analyze_occupational_patterns(self) -> list[ResearchQuestion]:
        """Analyze occupations and social status"""
        questions = []

        # Common Dutch historical occupations
        occupation_patterns = [
            r'\b(arbeider|worker|laborer)\b',
            r'\b(boer|farmer|landbouwer)\b',
            r'\b(bakker|baker)\b',
            r'\b(smid|blacksmith|schmied)\b',
            r'\b(timmerman|carpenter)\b',
            r'\b(kleermaker|tailor)\b',
            r'\b(schoenmaker|shoemaker)\b',
            r'\b(koopman|merchant|handelaar)\b'
        ]

        occupations_found = []
        for pattern in occupation_patterns:
            matches = re.findall(pattern, self.text_content, re.IGNORECASE)
            occupations_found.extend(matches)

        if occupations_found:
            occupation_counts = Counter([occ.lower() for occ in occupations_found])

            questions.append(ResearchQuestion(
                category="Social and Economic History",
                question="How did family occupations reflect regional economic conditions?",
                evidence=f"Occupations found: {', '.join(occupation_counts.keys())}",
                priority="medium",
                research_type="online",
                difficulty="moderate",
                potential_sources=["Guild records", "Economic histories", "Census records", "Trade records"]
            ))

            if 'arbeider' in occupation_counts or 'worker' in occupation_counts:
                questions.append(ResearchQuestion(
                    category="Industrial History",
                    question="What industrial developments affected family members who were laborers?",
                    evidence="Multiple family members listed as 'arbeider' (laborer)",
                    priority="low",
                    research_type="online",
                    difficulty="easy",
                    potential_sources=["Industrial histories", "Labor records", "Local newspapers", "Factory records"]
                ))

        return questions

    def analyze_naming_patterns(self) -> list[ResearchQuestion]:
        """Analyze naming conventions and variations"""
        questions = []

        if not self.people_data:
            return questions

        # Analyze name variations
        surnames = [p.get('surname', '') for p in self.people_data if p.get('surname')]
        # Note: removed surname_counts usage for linting compliance

        # Check for van Zanten / van Santen variations
        zanten_variations = [name for name in surnames if 'zanten' in name.lower() or 'santen' in name.lower()]

        if len(set(zanten_variations)) > 1:
            questions.append(ResearchQuestion(
                category="Name Variations",
                question="Why do we see different spellings of the family surname (van Zanten vs van Santen)?",
                evidence=f"Variations found: {', '.join(set(zanten_variations))}",
                priority="high",
                research_type="archival",
                difficulty="easy",
                potential_sources=["Civil registration", "Church records", "Name standardization histories"]
            ))

        # Analyze given name patterns
        given_names = []
        for person in self.people_data:
            names = person.get('given_names', '').split()
            given_names.extend(names)

        name_popularity = Counter(given_names)
        popular_names = [name for name, count in name_popularity.most_common(5) if count > 2]

        if popular_names:
            questions.append(ResearchQuestion(
                category="Naming Traditions",
                question="What naming traditions influenced the repeated use of certain given names?",
                evidence=f"Frequently used names: {', '.join(popular_names)}",
                priority="low",
                research_type="online",
                difficulty="easy",
                potential_sources=["Dutch naming traditions", "Religious influences", "Family patterns"]
            ))

        return questions

    def analyze_historical_context(self) -> list[ResearchQuestion]:
        """Generate questions about historical events and contexts"""
        questions = []

        # Extract years from text
        years = re.findall(r'\b(1[6-9]\d{2}|20[01]\d)\b', self.text_content)
        years = [int(year) for year in set(years)]

        if not years:
            return questions

        year_range = (min(years), max(years))

        # Check which historical periods the family lived through
        affected_periods = []
        for period_name, (start, end) in self.historical_periods.items():
            if year_range[0] <= end and year_range[1] >= start:
                affected_periods.append(period_name)

        if 'napoleonic' in affected_periods:
            questions.append(ResearchQuestion(
                category="Historical Context",
                question="How did the Napoleonic period (1795-1815) affect the family's civil registration and naming practices?",
                evidence=f"Family records span {year_range[0]}-{year_range[1]}, including Napoleonic era",
                priority="medium",
                research_type="online",
                difficulty="moderate",
                potential_sources=["Napoleonic civil registration", "Dutch history", "Administrative changes"]
            ))

        if 'wwii' in affected_periods:
            questions.append(ResearchQuestion(
                category="20th Century History",
                question="How did World War II impact family members living in the Netherlands?",
                evidence="Family records extend into WWII period",
                priority="high",
                research_type="archival",
                difficulty="difficult",
                potential_sources=["War records", "Resistance archives", "Municipal records", "Personal accounts"]
            ))

        return questions

    def analyze_religious_context(self) -> list[ResearchQuestion]:
        """Analyze religious affiliations and changes"""
        questions = []

        # Look for religious indicators
        religious_terms = [
            r'\b(gereformeerd|reformed)\b',
            r'\b(hervormd|protestant)\b',
            r'\b(katholiek|catholic|rooms)\b',
            r'\b(gedoopt|baptized|baptism)\b',
            r'\b(kerk|church|gemeente)\b'
        ]

        religious_mentions = []
        for pattern in religious_terms:
            matches = re.findall(pattern, self.text_content, re.IGNORECASE)
            religious_mentions.extend(matches)

        if religious_mentions:
            questions.append(ResearchQuestion(
                category="Religious History",
                question="What was the family's religious affiliation and did it change over time?",
                evidence=f"Religious terms found: {', '.join(set(religious_mentions))}",
                priority="medium",
                research_type="archival",
                difficulty="moderate",
                potential_sources=["Church records", "Baptism registers", "Marriage records", "Religious censuses"]
            ))

        return questions

    def query_llm_for_insights(self, text_sample: str) -> list[ResearchQuestion]:
        """Use Ollama LLM to generate additional research insights"""
        questions = []

        # Get Ollama configuration from Flask app
        config = current_app.config
        ollama_base_url = config.get('ollama_base_url', 'http://localhost:11434')
        ollama_model = config.get('OLLAMA_MODEL', 'qwen2.5:7b')

        # Create a focused prompt for research question generation
        prompt = f"""You are a genealogy research expert analyzing Dutch family history. Based on this text excerpt, identify 3-5 specific research questions that would help fill knowledge gaps or explore interesting patterns.

Text excerpt:
{text_sample[:2000]}

Focus on:
1. Missing information that could be found in archives
2. Historical context that affected the family
3. Patterns that suggest broader stories
4. Specific questions that could be answered with targeted research

Return only a JSON list in this format:
[
  {{
    "question": "Specific research question",
    "rationale": "Why this question is important",
    "research_type": "archival/online/dna/local_records",
    "difficulty": "easy/moderate/difficult"
  }}
]

JSON:"""

        try:
            response = requests.post(
                f"{ollama_base_url}/api/generate",
                json={
                    "model": ollama_model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"temperature": 0.3}
                },
                timeout=60
            )
            response.raise_for_status()

            response_text = response.json().get('response', '')

            # Extract JSON from response
            json_match = re.search(r'\[.*\]', response_text, re.DOTALL)
            if json_match:
                try:
                    llm_questions = json.loads(json_match.group(0))

                    for q in llm_questions:
                        questions.append(ResearchQuestion(
                            category="AI-Generated Insights",
                            question=q.get('question', ''),
                            evidence=q.get('rationale', ''),
                            priority="medium",
                            research_type=q.get('research_type', 'online'),
                            difficulty=q.get('difficulty', 'moderate'),
                            potential_sources=["To be determined based on research type"]
                        ))
                except json.JSONDecodeError:
                    logger.warning("Could not parse LLM response as JSON")

        except requests.RequestException as e:
            logger.warning(f"LLM query failed: {e}")

        return questions

    def generate_all_questions(self) -> list[ResearchQuestion]:
        """Generate comprehensive research questions

        Returns:
            List of generated research questions
        """
        logger.info("Generating research questions...")

        self.load_data()

        # Run different analysis methods
        self.research_questions.extend(self.analyze_missing_information_gaps())
        self.research_questions.extend(self.analyze_geographic_patterns())
        self.research_questions.extend(self.analyze_occupational_patterns())
        self.research_questions.extend(self.analyze_naming_patterns())
        self.research_questions.extend(self.analyze_historical_context())
        self.research_questions.extend(self.analyze_religious_context())

        # Use LLM for additional insights if text is available
        if self.text_content:
            # Take a representative sample of the text
            sample_text = self.text_content[1000:3000]  # Skip header content
            self.research_questions.extend(self.query_llm_for_insights(sample_text))

        logger.info(f"Generated {len(self.research_questions)} research questions")
        return self.research_questions

    def prioritize_questions(self) -> None:
        """Sort questions by priority and feasibility"""
        priority_order = {'high': 3, 'medium': 2, 'low': 1}
        difficulty_order = {'easy': 3, 'moderate': 2, 'difficult': 1}

        def score_question(q):
            priority_score = priority_order.get(q.priority, 1)
            difficulty_score = difficulty_order.get(q.difficulty, 1)
            return priority_score + difficulty_score

        self.research_questions.sort(key=score_question, reverse=True)

    def save_questions(self, output_file: str = "research_questions.json") -> None:
        """Save research questions to JSON file"""
        questions_data = {
            'metadata': {
                'generated_on': str(Path().absolute()),
                'total_questions': len(self.research_questions),
                'categories': list({q.category for q in self.research_questions})
            },
            'questions': [
                {
                    'category': q.category,
                    'question': q.question,
                    'evidence': q.evidence,
                    'priority': q.priority,
                    'research_type': q.research_type,
                    'difficulty': q.difficulty,
                    'potential_sources': q.potential_sources
                }
                for q in self.research_questions
            ]
        }

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(questions_data, f, indent=2, ensure_ascii=False)

        logger.info(f"Research questions saved to {output_file}")
        return output_file

    def get_summary(self) -> dict:
        """Get a structured summary of generated research questions

        Returns:
            Dict with summary statistics and categorized questions
        """
        if not self.research_questions:
            return {"total_questions": 0, "categories": {}}

        # Group by category
        categories = defaultdict(list)
        for q in self.research_questions:
            categories[q.category].append(q)

        summary = {
            "total_questions": len(self.research_questions),
            "categories": {}
        }

        for category, questions in categories.items():
            summary["categories"][category] = {
                "count": len(questions),
                "sample_questions": [
                    {
                        "question": q.question,
                        "priority": q.priority,
                        "difficulty": q.difficulty,
                        "research_type": q.research_type,
                        "evidence": q.evidence
                    }
                    for q in questions[:3]  # Top 3 per category
                ]
            }

        return summary
