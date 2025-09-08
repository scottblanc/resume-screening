#!/usr/bin/env python3
"""
Resume Extractor - AI-powered resume parsing and candidate data extraction.

This module provides functionality to extract structured data from resume files
using various LLM providers. It analyzes PDF files to extract candidate
information, skills, experience, and generates aggregate scores.

License: MIT License
Copyright (c) 2024 Scott White
See LICENSE file for full license text.
"""

import os
import re
import csv
import time
import logging
import sys
from typing import Dict, List, Optional, Type
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
import fitz  # PyMuPDF
import PyPDF2
from pydantic import BaseModel, Field
import instructor
from groq import Groq
from openai import OpenAI
import anthropic
import google.generativeai as genai
from tqdm import tqdm

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

"""
Pydantic model for structured resume data extraction.

CUSTOMIZATION NOTE: The skill fields and scoring categories below are examples
and can be fully customized to match your specific hiring requirements.

To customize:
1. Modify the fields in the "CUSTOMIZABLE SKILL ASSESSMENT" section
2. Update the aggregate scoring logic if needed
3. The dashboard will automatically adapt to display any fields present in the CSV

Common customizations:
- Add domain-specific technical skills
- Modify programming languages and frameworks
- Adjust company/university tier definitions
- Add industry-specific knowledge areas
"""
class ResumeData(BaseModel):
    # ==================== BASIC CANDIDATE INFORMATION ====================
    # These fields are typically kept unchanged
    resume_filename: str = Field(description="Original filename of the resume")
    candidate_name: str = Field(description="Full name of the candidate")
    email: str = Field(description="Email address of the candidate")
    github_link: str = Field(description="GitHub profile URL (if found)")
    linkedin_link: str = Field(description="LinkedIn profile URL (if found)")
    country: str = Field(description="Country of residence")
    city: str = Field(description="City of residence")
    
    # ==================== EDUCATION INFORMATION ====================
    # Customize university tier definitions and ranking systems as needed
    college_education_years: int = Field(description="Total years of college education (4 for bachelors, 6 for masters, 8+ for PhD)")
    highest_degree: str = Field(description="Highest degree obtained (e.g., Bachelors, Masters, PhD)")
    bachelors_university: str = Field(description="University attended for bachelor's degree")
    graduate_university: str = Field(description="University attended for graduate degree (Masters/PhD), empty if none")
    university_tier: int = Field(description="University tier for CS program (1=top tier like MIT/Stanford, 2=excellent like Purdue, 3=good, 4=average, 5=below average)")
    overall_world_ranking: int = Field(description="Overall world ranking of best university attended (1-2000+, 0 if unknown)")
    cs_world_ranking: int = Field(description="CS program world ranking of best university attended (1-500+, 0 if unknown)")
    bachelors_gpa: float = Field(description="GPA for bachelor's degree (0.0-4.0 scale, 0.0 if not mentioned)")
    masters_gpa: float = Field(description="GPA for master's degree (0.0-4.0 scale, 0.0 if not mentioned or no masters)")
    
    # ==================== WORK EXPERIENCE ====================
    # Customize company tier definitions and job level categories
    estimated_job_level: str = Field(description="Estimated job level (AMTS, MTS, SMTS, LMTS, PMTS based on experience and skills)")
    programming_experience_years: float = Field(description="Total years of programming/software development experience in industry")
    companies_worked: str = Field(description="List of companies worked at, ordered by recency, comma-separated")
    company_tier: int = Field(description="Tier of most impressive work experience (1=FAANG/top tech, 2=unicorn/well-known, 3=established company, 4=startup, 5=unknown)")
    cs_internships: int = Field(description="Number of CS-related internships")
    
    # ==================== CUSTOMIZABLE SKILL ASSESSMENT ====================
    # 🎯 CUSTOMIZE THIS SECTION FOR YOUR SPECIFIC REQUIREMENTS
    # 
    # Examples below are for a full-stack web development role with AI/ML focus.
    # Modify these fields to match your job requirements:
    # - Add/remove programming languages
    # - Change frameworks and tools
    # - Adjust skill categories
    # - Modify the 1-5 scale if needed
    
    # Core Programming Languages (customize list)
    javascript_skill_level: int = Field(description="JavaScript/TypeScript skill level (1=none, 2=basic, 3=intermediate, 4=advanced, 5=expert)")
    python_skill_level: int = Field(description="Python skill level (1=none, 2=basic, 3=intermediate, 4=advanced, 5=expert)")
    
    # Frontend Technologies (add/remove as needed)
    react_strength: int = Field(description="React.js expertise level (1=none, 2=basic, 3=intermediate, 4=advanced, 5=expert)")
    typescript_strength: int = Field(description="TypeScript expertise level (1=none, 2=basic, 3=intermediate, 4=advanced, 5=expert)")
    nextjs_strength: int = Field(description="Next.js expertise level (1=none, 2=basic, 3=intermediate, 4=advanced, 5=expert)")
    tailwind_strength: int = Field(description="Tailwind CSS expertise (1=none, 2=basic, 3=intermediate, 4=advanced, 5=expert)")
    
    # Backend & Infrastructure (customize for your stack)
    api_design_strength: int = Field(description="REST API design expertise (1=none, 2=basic, 3=intermediate, 4=advanced, 5=expert)")
    cloud_skill_level: int = Field(description="Cloud infrastructure skill level (1=none, 2=basic, 3=intermediate, 4=advanced, 5=expert)")
    cloud_experience_years: float = Field(description="Years of cloud experience (AWS, Azure, GCP)")
    aws_services_experience: str = Field(description="AWS services used (Lambda, S3, API Gateway, etc.)")
    database_technologies: str = Field(description="Database technologies used (PostgreSQL, MongoDB, DynamoDB, etc.)")
    
    # AI/ML Specialization (remove if not relevant)
    ai_experience_years: float = Field(description="Years of AI/ML experience")
    llm_skill_level: int = Field(description="LLM/NLP skill level (1=none, 2=basic, 3=intermediate, 4=advanced, 5=expert)")
    llm_experience_years: float = Field(description="Years of LLM/NLP experience")
    ai_tools_experience: str = Field(description="AI developer tools used (Cursor, Claude Code, Copilot, etc.)")
    llm_api_experience: str = Field(description="LLM APIs used (OpenAI, Anthropic, Gemini, etc.)")
    
    # Development Practices (adjust based on your workflow)
    git_strength: int = Field(description="Git/GitHub expertise (1=none, 2=basic, 3=intermediate, 4=advanced, 5=expert)")
    agile_strength: int = Field(description="Agile/Scrum expertise (1=none, 2=basic, 3=intermediate, 4=advanced, 5=expert)")
    
    # CS Fundamentals (typically kept for technical roles)
    algorithms_strength: int = Field(description="Algorithm/data structure strength (1-5 based on projects, education, competitions)")
    system_design_strength: int = Field(description="System design/architecture expertise (1=none, 2=basic, 3=intermediate, 4=advanced, 5=expert)")
    
    # Work Style & Leadership (adjust based on role level)
    startup_experience_strength: int = Field(description="Startup experience level (1=none, 2=minimal, 3=some, 4=significant, 5=extensive)")
    open_source_strength: int = Field(description="Open source contribution level (1=none, 2=minimal, 3=some, 4=active, 5=maintainer)")
    leadership_strength: int = Field(description="Leadership experience level (1=none, 2=minimal, 3=some lead, 4=team lead, 5=manager)")
    autonomy_indicators: str = Field(description="Evidence of autonomous work (freelance, solo projects, etc.)")
    
    # ==================== AGGREGATE SCORING ====================
    # These aggregate scores are calculated relative to experience level
    # Modify the categories below to match your skill assessment above
    academic_strength: int = Field(description="Academic strength relative to experience level (1-10, where 10=exceptional education for their career level)")
    cs_strength: int = Field(description="CS fundamentals strength relative to experience level (1-10, algorithms, system design, competitions)")
    industry_strength: int = Field(description="Industry experience strength relative to experience level (1-10, quality of companies and roles)")
    fullstack_strength: int = Field(description="Full-stack development strength relative to experience level (1-10, frontend + backend + cloud)")
    opensource_strength: int = Field(description="Open source contribution strength relative to experience level (1-10, contributions and impact)")
    accomplishments_strength: int = Field(description="Accomplishments strength relative to experience level (1-10, awards, publications, impact)")
    overall_score: float = Field(description="Average of all 6 strength scores")
    
    # ==================== ACCOMPLISHMENTS ====================
    accomplishment_1: str = Field(description="Most impressive accomplishment")
    accomplishment_2: str = Field(description="Second most impressive accomplishment")
    accomplishment_3: str = Field(description="Third most impressive accomplishment")

class ResumeLLMParser:
    def __init__(self, provider: str = "groq", model: str = "llama-3.3-70b-versatile", api_key: Optional[str] = None, max_workers: int = 4):
        """Initialize the LLM-based resume parser.
        
        Args:
            provider: The model provider to use (groq, openai, anthropic, gemini)
            model: The model to use. Works with any model supported by instructor for the chosen provider
            api_key: API key for the selected model provider
            max_workers: Maximum number of concurrent threads (default: 4)
        """
        self.provider = provider
        self.model = model
        self.api_key = api_key
        self.max_workers = max_workers
        self.rate_limit_lock = threading.Lock()
        self.last_request_time = 0
        # Initialize a client for testing connection
        self.client = self._initialize_client(provider, model, api_key)
        
    def _initialize_client(self, provider: str, model: str, api_key: Optional[str] = None):
        """Initialize the appropriate LLM client based on the provider."""
        if provider == "groq":
            final_api_key = api_key or os.getenv("GROQ_API_KEY")
            if not final_api_key:
                raise ValueError(
                    "❌ Groq API key required! Set GROQ_API_KEY environment variable or use --api-key\n"
                    "💡 Get your free API key at: https://console.groq.com/keys"
                )
            try:
                groq_client = Groq(api_key=final_api_key)
                return instructor.from_groq(groq_client, model=model)
            except Exception as e:
                raise ValueError(f"❌ Failed to initialize Groq client: {e}\n💡 Check your API key is valid")
                
        elif provider == "openai":
            final_api_key = api_key or os.getenv("OPENAI_API_KEY")
            if not final_api_key:
                raise ValueError(
                    "❌ OpenAI API key required! Set OPENAI_API_KEY environment variable or use --api-key\n"
                    "💡 Get your API key at: https://platform.openai.com/api-keys"
                )
            try:
                openai_client = OpenAI(api_key=final_api_key)
                return instructor.from_openai(openai_client, model=model)
            except Exception as e:
                raise ValueError(f"❌ Failed to initialize OpenAI client: {e}\n💡 Check your API key is valid")
                
        elif provider == "anthropic":
            final_api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
            if not final_api_key:
                raise ValueError(
                    "❌ Anthropic API key required! Set ANTHROPIC_API_KEY environment variable or use --api-key\n"
                    "💡 Get your API key at: https://console.anthropic.com/account/keys"
                )
            try:
                anthropic_client = anthropic.Anthropic(api_key=final_api_key)
                return instructor.from_anthropic(anthropic_client, model=model, mode=instructor.Mode.ANTHROPIC_JSON)
            except Exception as e:
                raise ValueError(f"❌ Failed to initialize Anthropic client: {e}\n💡 Check your API key is valid")
                
        elif provider == "gemini":
            final_api_key = api_key or os.getenv("GOOGLE_API_KEY")
            if not final_api_key:
                raise ValueError(
                    "❌ Google API key required! Set GOOGLE_API_KEY environment variable or use --api-key\n"
                    "💡 Get your API key at: https://makersuite.google.com/app/apikey"
                )
            try:
                genai.configure(api_key=final_api_key)
                gemini_model = genai.GenerativeModel(model_name=model)
                return instructor.from_gemini(client=gemini_model, mode=instructor.Mode.GEMINI_JSON)
            except Exception as e:
                raise ValueError(f"❌ Failed to initialize Gemini client: {e}\n💡 Check your API key is valid")
        else:
            raise ValueError(f"❌ Unsupported provider: {provider}\n💡 Supported providers: groq, openai, anthropic, gemini")
    
    def extract_text_from_pdf(self, pdf_path: str) -> str:
        """Extract text from PDF file including hyperlinks."""
        try:
            # Try with PyMuPDF first (better extraction)
            doc = fitz.open(pdf_path)
            text = ""
            links = []
            
            for page in doc:
                # Extract regular text
                page_text = page.get_text()
                
                # Extract hyperlinks
                page_links = page.get_links()
                for link in page_links:
                    if 'uri' in link:
                        uri = link['uri']
                        # Add the link to our text for LLM processing
                        if 'github' in uri.lower():
                            page_text += f"\nGitHub: {uri}"
                        elif 'linkedin' in uri.lower():
                            page_text += f"\nLinkedIn: {uri}"
                        else:
                            page_text += f"\nLink: {uri}"
                
                text += page_text
            
            doc.close()
            return text
        except Exception as e:
            logging.warning(f"PyMuPDF failed for {pdf_path}: {e}, trying PyPDF2")
            try:
                # Fallback to PyPDF2
                with open(pdf_path, 'rb') as file:
                    pdf_reader = PyPDF2.PdfReader(file)
                    text = ""
                    for page in pdf_reader.pages:
                        text += page.extract_text()
                    return text
            except Exception as e2:
                logging.error(f"Both PDF extraction methods failed for {pdf_path}: {e2}")
                return ""
    
    def _get_client(self):
        """Get a fresh client instance for thread-safe usage."""
        return self._initialize_client(self.provider, self.model, self.api_key)
    
    def _rate_limited_request(self, delay: float = 0.5):
        """Ensure minimum delay between requests to respect rate limits."""
        with self.rate_limit_lock:
            now = time.time()
            time_since_last = now - self.last_request_time
            if time_since_last < delay:
                time.sleep(delay - time_since_last)
            self.last_request_time = time.time()
    
    def parse_resume_with_llm(self, resume_text: str, filename: str) -> Optional[ResumeData]:
        """Use LLM to parse and extract structured data from resume text."""
        
        prompt = f"""Analyze this resume and extract the following information. Be precise and realistic in your assessments.

IMPORTANT: 
- Set resume_filename to: {filename}
- ALL field names must match EXACTLY (no extra spaces or typos)
- ALL required fields must be present - do not skip any fields
- Use empty string "" for missing links, not null
- Return VALID JSON only - no extra text, tags, or formatting
- Do not add [/function] or any closing tags

RESUME TEXT:
{resume_text[:8000]}  # Limit text to avoid token limits

Please extract and evaluate:

1. Basic Information:
   - Full name (if not clear from text, extract from filename) - avoid special characters like apostrophes
   - Email address
   - GitHub and LinkedIn URLs (return empty string if not found)
   - Location (country and city)
   - Estimated job level based on experience and skills:
     * Intern: Student or recent grad with no professional experience, internships only
     * AMTS (Associate Member of Technical Staff): 0-2 years, entry level, recent grad
     * MTS (Member of Technical Staff): 2-4 years, mid-level individual contributor
     * SMTS (Senior Member of Technical Staff): 4-7 years, senior individual contributor
     * LMTS (Lead Member of Technical Staff): 7-10 years, tech lead, some management
     * PMTS (Principal Member of Technical Staff): 10+ years, principal engineer, architect

2. Experience (use decimal years like 2.5 when appropriate):
   - Years of programming/software development experience in professional settings (not including education)
   - Years of AI/ML experience (use 0 if none)
   - Years of cloud experience (AWS, Azure, GCP - use 0 if none)
   - Years of LLM/NLP experience (use 0 if none)

3. Education:
   - Total years of college education (4 for bachelors, 6 for masters, 8+ for PhD)
   - Highest degree obtained
   - Bachelor's university name (full name)
   - Graduate university name (Masters/PhD) - empty string if none
   - University tier for CS program (consider best university attended):
     * Tier 1: Top schools (MIT, Stanford, CMU, Berkeley, etc.)
     * Tier 2: Excellent schools (Purdue, UCLA, UCSD, Georgia Tech, etc.)
     * Tier 3: Good schools (state universities, well-known regionals)
     * Tier 4: Average schools
     * Tier 5: Below average or unknown
   - Overall world ranking of best university attended (estimate 1-2000+, use 0 if completely unknown)
     Examples Overall: MIT=2, Stanford=3, Harvard=1, Berkeley=14, Purdue=126, Arizona State=1100, Western Michigan=1200
   - CS program world ranking of best university attended (estimate 1-500+, use 0 if completely unknown)  
     Examples CS: MIT=1, Stanford=2, Berkeley=3, Purdue=20, Arizona State=85, Western Michigan=200+
   - Bachelor's GPA (0.0-4.0 scale, use 0.0 if not mentioned)
   - Master's GPA (0.0-4.0 scale, use 0.0 if not mentioned or no master's degree)

4. Work Experience:
   - List ALL companies worked at, ordered from most recent to oldest (comma-separated)
   - Company tier based on most impressive employer:
     * Tier 1: FAANG, top tech companies (Google, Meta, Amazon, Microsoft, Apple, OpenAI, etc.)
     * Tier 2: Well-known tech companies, unicorns (Uber, Airbnb, Stripe, etc.)
     * Tier 3: Established non-tech companies, consulting firms
     * Tier 4: Startups, smaller companies
     * Tier 5: Unknown or no work experience

5. Skill Levels (1-5 scale):
   - JavaScript/TypeScript skill level:
     * 1 = No experience
     * 2 = Basic (learning, tutorials, simple projects)
     * 3 = Intermediate (used professionally, can build features)
     * 4 = Advanced (expert user, complex projects, mentors others)
     * 5 = Expert (thought leader, open source contributor, architect level)
   
   - Python skill level (same 1-5 scale)
   
   - Cloud infrastructure skill level (AWS/Azure/GCP):
     * 1 = No experience
     * 2 = Basic (used some services)
     * 3 = Intermediate (deployed applications, used multiple services)
     * 4 = Advanced (designed architectures, cost optimization, security)
     * 5 = Expert (certified, large-scale systems, infrastructure as code)
   
   - LLM/NLP skill level:
     * 1 = No experience
     * 2 = Basic (used APIs, simple prompts)
     * 3 = Intermediate (fine-tuning, RAG, prompt engineering)
     * 4 = Advanced (built production systems, model optimization)
     * 5 = Expert (research, custom models, published papers)

   - Number of CS-related internships

6. Frontend Stack Skills (1-5 scale):
   - React.js strength (1=none, 5=expert with production experience)
   - TypeScript strength (1=none, 5=expert level)
   - Next.js strength (1=none, 5=expert)
   - REST API design strength (1=none, 5=designed complex APIs)
   - Tailwind CSS strength (1=none, 5=expert)
   - Git/GitHub strength (1=none, 5=advanced workflows)
   - Agile/Scrum strength (1=none, 5=led sprints)
   
   Also extract:
   - AWS services used (list specific services like Lambda, S3, etc.)
   - Database technologies used (PostgreSQL, MongoDB, DynamoDB, etc.)
   - AI developer tools used (Cursor, Claude Code, Copilot, etc.)
   - LLM APIs used (OpenAI, Anthropic, Gemini, etc.)

7. Work Style & Independence Indicators:
   - Startup experience strength (1=none, 5=founded or early employee)
   - Open source contribution strength (1=none, 5=maintainer)
   - Leadership strength (1=none, 5=managed teams)
   - Evidence of autonomous work (freelance, solo projects, etc.)

8. CS Fundamentals:
   - Algorithm/data structure strength (1-5, based on education, competitions, projects)
   - System design strength (1=none, 5=designed large systems)

9. EXPERIENCE-RELATIVE AGGREGATE SCORES (1-10 scale, ALL RELATIVE TO JOB LEVEL):
   IMPORTANT: Score these relative to what would be exceptional for someone at their experience level.
   An AMTS should be compared to other AMTS-level engineers, not to PMTS-level engineers.
   
   - Academic Strength (1-10): Consider overall/CS world ranking, GPA, degrees, research FOR THEIR LEVEL
     * 10 = Top 5 world universities (MIT, Stanford, Harvard, etc.) with high GPA for their level
     * 8-9 = Top 50 world universities with good performance for their level
     * 6-7 = Top 200 world universities OR strong GPA at lower-ranked school for their level
     * 4-5 = Top 500-1000 universities with average performance for their level
     * 1-3 = Universities ranked 1000+ or poor academic performance for their level
     IMPORTANT: Weight CS ranking more heavily than overall ranking for CS-related roles
   
   - CS Strength (1-10): Algorithms, data structures, system design, competitions
     * 10 = International competition winner, exceptional CS knowledge for experience level
     * 8-9 = Strong algorithmic thinking, competition experience for experience level
     * 6-7 = Solid CS fundamentals for their experience level
     * 4-5 = Basic CS knowledge for level
     * 1-3 = Weak CS fundamentals for level
   
   - Industry Strength (1-10): Quality of work experience relative to experience level
     * 10 = FAANG/top tech companies, exceptional roles for experience level
     * 8-9 = Excellent companies for someone at their experience level
     * 6-7 = Good industry experience for experience level
     * 4-5 = Some industry experience appropriate for level
     * 1-3 = Below average experience for level
   
   - Full-Stack Strength (1-10): Frontend + Backend + Cloud capabilities for experience level
     * 10 = Production-level full-stack expertise exceptional for experience level
     * 8-9 = Strong across the stack for their experience level
     * 6-7 = Competent in multiple areas for level
     * 4-5 = Some full-stack exposure for level
     * 1-3 = Limited full-stack skills for level
   
   - Open Source Strength (1-10): GitHub contributions, projects relative to experience level
     * 10 = Major open source contributor/maintainer exceptional for experience level
     * 8-9 = Active contributor with significant projects for experience level
     * 6-7 = Some contributions and personal projects for level
     * 4-5 = Few personal projects for level
     * 1-3 = No open source presence
   
   - Accomplishments Strength (1-10): Awards, publications, impact relative to experience level
     * 10 = Exceptional achievements for experience level (founded company, published papers, major awards)
     * 8-9 = Impressive accomplishments for someone at their experience level
     * 6-7 = Good achievements for experience level
     * 4-5 = Some noteworthy items for level
     * 1-3 = Few accomplishments for level
   
   - Overall Score: Calculate the average of the above 6 scores (round to 1 decimal)

10. Top 3 Accomplishments:
   - Extract the three most impressive accomplishments from the resume
   - Look for quantifiable impacts, awards, publications, leadership roles, etc.

Be accurate and conservative in your estimates. If information is not clear, make reasonable inferences based on the context."""

        try:
            # Rate limit API calls
            self._rate_limited_request()
            
            # Get a thread-local client
            client = self._get_client()
            
            # Make the API call with retry logic
            for attempt in range(3):
                try:
                    logging.info(f"Sending resume to LLM for parsing (attempt {attempt + 1}/3)")
                    
                    response = client.chat.completions.create(
                        response_model=ResumeData,
                        messages=[{"role": "user", "content": prompt}],
                        max_retries=2  # Let instructor handle some retries too
                    )
                    
                    return response
                    
                except Exception as e:
                    error_str = str(e)
                    
                    # Handle rate limits and server errors
                    if ("429" in error_str or "rate limit" in error_str.lower() or 
                        "500" in error_str or "internal server error" in error_str.lower()):
                        wait_time = 10 * (attempt + 1)  # Exponential backoff
                        if "500" in error_str:
                            logging.warning(f"Server error, waiting {wait_time}s before retry: {error_str[:100]}")
                        else:
                            logging.warning(f"Rate limit hit, waiting {wait_time}s before retry")
                        time.sleep(wait_time)
                        continue
                    
                    # Handle validation errors - try once more with stricter prompt
                    elif ("tool call validation failed" in error_str or 
                          "Failed to call a function" in error_str) and attempt < 2:
                        logging.warning(f"Validation error, retrying with stricter prompt: {error_str[:200]}")
                        # Add stricter instructions for second attempt
                        strict_prompt = prompt + """

CRITICAL: Your response must include ALL these exact field names:
resume_filename, candidate_name, email, github_link, linkedin_link, country, city, estimated_job_level, programming_experience_years, ai_experience_years, college_education_years, highest_degree, bachelors_university, graduate_university, university_tier, overall_world_ranking, cs_world_ranking, bachelors_gpa, masters_gpa, companies_worked, company_tier, javascript_skill_level, python_skill_level, cloud_skill_level, llm_skill_level, cs_internships, cloud_experience_years, llm_experience_years, react_strength, typescript_strength, nextjs_strength, api_design_strength, tailwind_strength, git_strength, agile_strength, aws_services_experience, database_technologies, ai_tools_experience, llm_api_experience, startup_experience_strength, open_source_strength, leadership_strength, autonomy_indicators, algorithms_strength, system_design_strength, academic_strength, cs_strength, industry_strength, fullstack_strength, opensource_strength, accomplishments_strength, overall_score, accomplishment_1, accomplishment_2, accomplishment_3

EXACT field count required: 50 fields
DO NOT add extra spaces, typos, or skip any fields.
Return clean JSON without any extra tags or text."""
                        
                        prompt = strict_prompt
                        continue
                    else:
                        raise
                        
        except Exception as e:
            logging.error(f"Failed to parse resume with LLM: {e}")
            return None
    
    def process_resume(self, pdf_path: str) -> Optional[Dict]:
        """Process a single resume PDF file."""
        filename = os.path.basename(pdf_path)
        
        # Check if file exists and is readable
        if not os.path.exists(pdf_path):
            logging.error(f"❌ File not found: {pdf_path}")
            return None
            
        if not os.access(pdf_path, os.R_OK):
            logging.error(f"❌ Cannot read file (permission denied): {filename}")
            return None
        
        # Extract text from PDF
        try:
            text = self.extract_text_from_pdf(pdf_path)
            if not text or len(text.strip()) < 50:
                logging.warning(f"⚠️ Little or no text extracted from {filename} (might be image-based PDF)")
                return None
        except Exception as e:
            logging.error(f"❌ PDF extraction failed for {filename}: {str(e)[:100]}...")
            return None
        
        # Parse with LLM
        try:
            resume_data = self.parse_resume_with_llm(text, filename)
            if not resume_data:
                logging.warning(f"⚠️ LLM parsing returned no data for {filename}")
                return None
        except Exception as e:
            logging.error(f"❌ LLM parsing failed for {filename}: {str(e)[:100]}...")
            return None
        
        # Convert to dictionary
        try:
            return resume_data.dict()
        except Exception as e:
            logging.error(f"❌ Data conversion failed for {filename}: {str(e)[:100]}...")
            return None

    def process_resume_parallel_safe(self, pdf_path: str) -> tuple[str, Optional[Dict], Optional[str]]:
        """Thread-safe wrapper for process_resume that returns (path, result, error)."""
        try:
            result = self.process_resume(pdf_path)
            return (pdf_path, result, None)
        except Exception as e:
            error_msg = f"Processing error: {str(e)[:100]}..."
            return (pdf_path, None, error_msg)
    
    def process_all_resumes(self, directory: str, output_file: str = 'resume_analysis.csv', 
                           sample_size: Optional[int] = None):
        """Process all PDF resumes in directory and subdirectories.
        
        Args:
            directory: Root directory to search for PDFs
            output_file: Output CSV filename
            sample_size: Optional limit on number of resumes to process
        """
        results = []
        errors = []
        pdf_files = []
        
        # Check for existing results to resume from
        already_processed = set()
        if os.path.exists(output_file):
            logging.info(f"Found existing output file {output_file}, checking for processed resumes...")
            try:
                with open(output_file, 'r') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        results.append(row)
                        already_processed.add(row['resume_filename'])
                logging.info(f"Resuming from existing file with {len(already_processed)} already processed resumes")
            except Exception as e:
                logging.warning(f"Could not read existing file: {e}")
        
        # Check for temp file if main file doesn't exist
        elif os.path.exists(f"{output_file}.tmp"):
            logging.info(f"Found temp file {output_file}.tmp, resuming from there...")
            try:
                with open(f"{output_file}.tmp", 'r') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        results.append(row)
                        already_processed.add(row['resume_filename'])
                logging.info(f"Resuming from temp file with {len(already_processed)} already processed resumes")
            except Exception as e:
                logging.warning(f"Could not read temp file: {e}")
        
        # Find all PDF files
        for root, dirs, files in os.walk(directory):
            for file in files:
                if file.endswith('.pdf') and 'resume' in file.lower():
                    pdf_files.append(os.path.join(root, file))
        
        # Filter out already processed files
        pdf_files_to_process = []
        for pdf_path in pdf_files:
            filename = os.path.basename(pdf_path)
            if filename not in already_processed:
                pdf_files_to_process.append(pdf_path)
        
        # Limit to sample size if specified (after filtering already processed)
        if sample_size:
            remaining_to_process = sample_size - len(already_processed)
            if remaining_to_process > 0:
                pdf_files_to_process = pdf_files_to_process[:remaining_to_process]
            else:
                pdf_files_to_process = []
        
        total_found = len(pdf_files)
        total_to_process = len(pdf_files_to_process)
        total_already_done = len(already_processed)
        
        logging.info(f"Found {total_found} PDF resume files total")
        logging.info(f"Already processed: {total_already_done}")
        logging.info(f"Remaining to process: {total_to_process}")
        
        if total_to_process == 0:
            logging.info("No new resumes to process!")
            return
        
        # Process resumes in parallel
        success_count = 0
        pbar = tqdm(
            total=len(pdf_files_to_process),
            desc=f"📄 Processing resumes ({self.max_workers} workers)", 
            unit="resume",
            bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}] {postfix}"
        )
        
        try:
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                # Submit all jobs
                future_to_path = {
                    executor.submit(self.process_resume_parallel_safe, pdf_path): pdf_path 
                    for pdf_path in pdf_files_to_process
                }
                
                completed = 0
                for future in as_completed(future_to_path):
                    completed += 1
                    pdf_path, result, error = future.result()
                    filename = os.path.basename(pdf_path)
                    
                    # Update progress bar
                    pbar.set_postfix_str(f"Latest: {filename[:25]}...")
                    
                    if result:
                        results.append(result)
                        success_count += 1
                        pbar.set_description(f"📄 Processing resumes (✅ {success_count} successful)")
                    else:
                        # Track failed resumes
                        error_reason = error or 'LLM parsing failed - check resume format and content'
                        errors.append({
                            'resume_filename': filename,
                            'pdf_path': pdf_path,
                            'error_time': time.strftime('%Y-%m-%d %H:%M:%S'),
                            'error_reason': error_reason
                        })
                        pbar.set_description(f"📄 Processing resumes (⚠️ {len(errors)} failed)")
                    
                    pbar.update(1)
                    
                    # Save intermediate results every 20 completed resumes
                    if completed % 20 == 0:
                        try:
                            self._save_results(results, f"{output_file}.tmp")
                            self._save_errors(errors, f"{output_file.replace('.csv', '_errors.csv')}")
                            processed_count = len([r for r in results if isinstance(r, dict)])
                            pbar.write(f"💾 Saved intermediate results ({processed_count} total processed)")
                        except Exception as e:
                            pbar.write(f"⚠️ Warning: Failed to save intermediate results: {e}")
                            
        except KeyboardInterrupt:
            pbar.write(f"\n🛑 Processing interrupted by user. Saving progress...")
            pbar.close()
            # Save what we have so far
            if results:
                self._save_results(results, f"{output_file}.interrupted")
                pbar.write(f"💾 Partial results saved to {output_file}.interrupted")
            sys.exit(1)
        finally:
            pbar.close()
        
        # Save final results with better feedback
        if results:
            self._save_results(results, output_file)
            successful_count = len([r for r in results if isinstance(r, dict) and 'resume_filename' in r])
            
            print(f"\n🎉 Processing Complete!")
            print(f"✅ Successfully processed: {successful_count} resumes")
            print(f"📁 Results saved to: {output_file}")
            
            # Clean up temp file
            temp_file = f"{output_file}.tmp"
            if os.path.exists(temp_file):
                os.remove(temp_file)
                print(f"🧹 Cleaned up temporary file: {temp_file}")
        else:
            print(f"\n❌ No resumes were successfully processed!")
            print(f"💡 Troubleshooting tips:")
            print(f"   • Check that PDF files contain readable text")
            print(f"   • Verify your API key is valid and has sufficient credits")
            print(f"   • Try with --sample 1 to test a single resume")
            print(f"   • Check the error log for specific issues")
        
        # Save error report with helpful feedback
        if errors:
            error_file = output_file.replace('.csv', '_errors.csv')
            self._save_errors(errors, error_file)
            error_count = len(errors)
            
            print(f"\n⚠️ Encountered {error_count} errors during processing")
            print(f"📋 Error details saved to: {error_file}")
            
            if error_count > 0:
                print(f"\n💡 Common solutions:")
                print(f"   • PDF extraction failed: Try different resume files or check file corruption")
                print(f"   • Rate limits: The script includes delays, but you may need longer pauses")
                print(f"   • API errors: Check your API key and account limits")
                print(f"   • Parsing errors: Some resumes may have unusual formatting")
        
        # Final summary
        total_attempted = len(pdf_files_to_process)
        if total_attempted > 0:
            success_rate = (success_count / total_attempted) * 100
            print(f"\n📊 Final Summary:")
            print(f"   📄 Total attempted: {total_attempted}")
            print(f"   ✅ Successful: {success_count}")
            print(f"   ❌ Failed: {len(errors)}")
            print(f"   📈 Success rate: {success_rate:.1f}%")
    
    def _save_results(self, results: List[Dict], output_file: str):
        """Save results to CSV file."""
        if not results:
            return
            
        fieldnames = [
            'resume_filename', 'candidate_name', 'email', 'github_link', 'linkedin_link', 
            'country', 'city', 'estimated_job_level', 'programming_experience_years', 'ai_experience_years',
            'college_education_years', 'highest_degree', 'bachelors_university', 'graduate_university',
            'university_tier', 'overall_world_ranking', 'cs_world_ranking', 'bachelors_gpa', 'masters_gpa',
            'companies_worked', 'company_tier', 
            'javascript_skill_level', 'python_skill_level', 'cloud_skill_level', 'llm_skill_level',
            'cs_internships', 'cloud_experience_years', 'llm_experience_years',
            # Frontend Stack
            'react_strength', 'typescript_strength', 'nextjs_strength', 'api_design_strength',
            'tailwind_strength', 'git_strength', 'agile_strength',
            'aws_services_experience', 'database_technologies', 'ai_tools_experience', 'llm_api_experience',
            # Work style
            'startup_experience_strength', 'open_source_strength', 'leadership_strength', 'autonomy_indicators',
            # CS fundamentals
            'algorithms_strength', 'system_design_strength',
            # Age-Relative Aggregate Scores
            'academic_strength', 'cs_strength', 'industry_strength', 'fullstack_strength',
            'opensource_strength', 'accomplishments_strength', 'overall_score',
            # Accomplishments
            'accomplishment_1', 'accomplishment_2', 'accomplishment_3'
        ]
        
        with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(results)

    def _save_errors(self, errors: List[Dict], error_file: str):
        """Save error report to CSV file."""
        if not errors:
            return
        
        fieldnames = ['resume_filename', 'pdf_path', 'error_time', 'error_reason']
        
        with open(error_file, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(errors)

def main():
    """Main function to run the resume parser."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='🤖 AI-powered resume extraction and analysis',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python resume_extractor.py                          # Process all PDFs in current directory using Groq
  python resume_extractor.py --sample 5               # Test with 5 resumes
  python resume_extractor.py --provider openai --model gpt-4   # Use OpenAI GPT-4
  python resume_extractor.py --provider anthropic --model claude-3-5-haiku-20241022  # Use Claude
  python resume_extractor.py --workers 8              # Use 8 parallel workers (faster)
  python resume_extractor.py --directory /path/to/resumes --output results.csv

Set API keys via environment variables:
  export GROQ_API_KEY="your_key_here"
  export OPENAI_API_KEY="your_key_here"  
  export ANTHROPIC_API_KEY="your_key_here"
  export GOOGLE_API_KEY="your_key_here"
        """
    )
    parser.add_argument('--provider', default='groq', 
                       choices=['groq', 'openai', 'anthropic', 'gemini'],
                       help='Model provider to use (default: groq)')
    parser.add_argument('--model', default='llama-3.3-70b-versatile', 
                       help='Model name to use. Works with any model supported by instructor for the chosen provider (default: llama-3.3-70b-versatile)')
    parser.add_argument('--api-key', help='API key for the model provider (or set via environment)')
    parser.add_argument('--output', default='candidates.csv', help='Output CSV filename (default: candidates.csv)')
    parser.add_argument('--sample', type=int, help='Process only N resumes for testing (default: all)')
    parser.add_argument('--directory', default='.', help='Directory to search for resumes (default: current)')
    parser.add_argument('--workers', type=int, default=4, help='Number of parallel workers (default: 4, max recommended: 8)')
    
    args = parser.parse_args()
    
    print(f"🚀 Starting resume extraction with {args.provider}/{args.model}")
    print(f"📂 Searching directory: {args.directory}")
    print(f"📄 Output file: {args.output}")
    print(f"⚙️ Parallel workers: {args.workers}")
    if args.sample:
        print(f"🔬 Sample mode: processing only {args.sample} resumes")
    print()
    
    try:
        # Initialize parser
        resume_parser = ResumeLLMParser(provider=args.provider, model=args.model, api_key=args.api_key, max_workers=args.workers)
        print(f"✅ Successfully initialized {args.provider}/{args.model} client with {args.workers} workers")
        
        # Process resumes
        resume_parser.process_all_resumes(
            directory=args.directory,
            output_file=args.output,
            sample_size=args.sample
        )
        
    except ValueError as e:
        print(f"\n{str(e)}")
        sys.exit(1)
    except KeyboardInterrupt:
        print(f"\n🛑 Process interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        print(f"💡 This might be a bug. Please check:")
        print(f"   • Your internet connection")
        print(f"   • That all required packages are installed: pip install -r requirements.txt")
        print(f"   • That your PDF files are not corrupted")
        sys.exit(1)

if __name__ == "__main__":
    main()
