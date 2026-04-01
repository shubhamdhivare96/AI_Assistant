"""
LLM Service for AI Assistant
Supports: Google Gemini (primary), Groq (fallback #1), AWS Nova Pro (fallback #2)
Updated to use new google-genai SDK
"""
import os
import json
import logging
from typing import List, Dict, Any, Optional
import boto3

# Try new SDK first, fallback to old if needed
try:
    from google import genai
    from google.genai import types
    GENAI_NEW = True
    logger = logging.getLogger(__name__)
    logger.info("Using new google-genai SDK")
except ImportError:
    try:
        import google.generativeai as genai
        GENAI_NEW = False
        logger = logging.getLogger(__name__)
        logger.warning("Using deprecated google.generativeai - please upgrade to google-genai")
    except ImportError:
        raise ImportError("Neither google-genai nor google.generativeai is installed")

from groq import Groq
from app.config import get_settings
from app.core.resilience import resilient_call, llm_breaker, groq_breaker, nova_breaker, RateLimitError

logger = logging.getLogger(__name__)

class LLMService:
    """Service for interacting with LLM providers"""
    
    def __init__(self):
        self.settings = get_settings()
        self.primary_client = None    # Gemini
        self.fallback_client = None   # Groq
        self.nova_client = None       # AWS Nova Pro (fallback #2)
        self.initialize_clients()
    
    def initialize_clients(self):
        """Initialize LLM clients"""
        try:
            # Primary: Google Gemini
            if self.settings.GOOGLE_API_KEY:
                if GENAI_NEW:
                    # New SDK
                    client = genai.Client(api_key=self.settings.GOOGLE_API_KEY)
                    self.primary_client = client
                    logger.info("Gemini client initialized (new SDK)")
                else:
                    # Old SDK (deprecated)
                    genai.configure(api_key=self.settings.GOOGLE_API_KEY)
                    self.primary_client = genai.GenerativeModel(self.settings.LLM_MODEL)
                    logger.info("Gemini client initialized (deprecated SDK)")
            
            # Fallback #1: Groq
            if self.settings.GROQ_API_KEY:
                self.fallback_client = Groq(api_key=self.settings.GROQ_API_KEY)
                logger.info("Groq fallback client initialized")
            
            # Fallback #2: AWS Bedrock Nova Pro
            if self.settings.AWS_ACCESS_KEY_ID and self.settings.AWS_ACCESS_KEY_ID != 'your_aws_access_key_here':
                self.nova_client = boto3.client(
                    'bedrock-runtime',
                    aws_access_key_id=self.settings.AWS_ACCESS_KEY_ID,
                    aws_secret_access_key=self.settings.AWS_SECRET_ACCESS_KEY,
                    region_name=self.settings.AWS_REGION
                )
                logger.info(f"AWS Nova Pro fallback client initialized (model: {self.settings.NOVA_LLM_MODEL})")
            else:
                logger.warning("AWS credentials not configured — Nova Pro fallback unavailable")
                
        except Exception as e:
            logger.error(f"Failed to initialize LLM clients: {str(e)}")
            raise
    
    async def generate_response(
        self, 
        messages: List[Dict[str, str]], 
        temperature: float = 0.7,
        max_tokens: int = 1000
    ) -> str:
        """Generate response: Gemini → Groq → Nova Pro"""
        # --- Tier 1: Gemini ---
        try:
            return await self._generate_gemini_response(messages, temperature, max_tokens)
        except RateLimitError as e:
            logger.warning(f"Gemini rate limited (quota exhausted), switching to Groq: {str(e)[:120]}")
        except Exception as e:
            logger.warning(f"Gemini failed: {str(e)[:120]}, trying Groq fallback")
        
        # --- Tier 2: Groq ---
        try:
            return await self._generate_groq_response(messages, temperature, max_tokens)
        except Exception as e2:
            logger.warning(f"Groq failed: {str(e2)[:120]}, trying Nova Pro fallback")
        
        # --- Tier 3: AWS Nova Pro ---
        try:
            return await self._generate_nova_response(messages, temperature, max_tokens)
        except Exception as e3:
            logger.error(f"All LLM providers failed. Nova error: {str(e3)[:120]}")
            raise Exception("All LLM providers exhausted (Gemini, Groq, Nova Pro)")
    
    async def _generate_gemini_response(
        self, 
        messages: List[Dict[str, str]], 
        temperature: float,
        max_tokens: int
    ) -> str:
        """Generate response using Google Gemini"""
        @resilient_call(llm_breaker, max_retries=3)
        async def _call_gemini():
            # Convert messages to Gemini format
            prompt = self._messages_to_prompt(messages)
            
            try:
                if GENAI_NEW:
                    # New SDK
                    response = self.primary_client.models.generate_content(
                        model=self.settings.LLM_MODEL,
                        contents=prompt,
                        config=types.GenerateContentConfig(
                            temperature=temperature,
                            max_output_tokens=max_tokens
                        )
                    )
                    return response.text
                else:
                    # Old SDK (deprecated)
                    response = self.primary_client.generate_content(
                        prompt,
                        generation_config=genai.types.GenerationConfig(
                            temperature=temperature,
                            max_output_tokens=max_tokens
                        )
                    )
                    return response.text
            except Exception as e:
                err_str = str(e)
                # Detect 429 rate limit / quota exhausted — don't retry, go straight to Groq
                if '429' in err_str or 'RESOURCE_EXHAUSTED' in err_str:
                    raise RateLimitError(f"Gemini quota exhausted: {err_str[:200]}")
                raise
        
        return await _call_gemini()
    
    async def _generate_groq_response(
        self, 
        messages: List[Dict[str, str]], 
        temperature: float,
        max_tokens: int
    ) -> str:
        """Generate response using Groq"""
        @resilient_call(groq_breaker, max_retries=3)  # Use separate breaker - independent from Gemini
        async def _call_groq():
            response = self.fallback_client.chat.completions.create(
                model=self.settings.FALLBACK_LLM_MODEL,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )
            return response.choices[0].message.content
        
        return await _call_groq()
    
    async def _generate_nova_response(
        self,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: int
    ) -> str:
        """Generate response using AWS Bedrock Nova Pro (fallback #2)"""
        if not self.nova_client:
            raise Exception("Nova Pro client not initialized (check AWS credentials)")
        
        @resilient_call(nova_breaker, max_retries=2)
        async def _call_nova():
            # Bedrock Converse API: split system vs conversation messages
            system_prompt = []
            conversation = []
            
            for msg in messages:
                role = msg.get('role', 'user')
                content = msg.get('content', '')
                if role == 'system':
                    system_prompt.append({"text": content})
                else:
                    conversation.append({
                        "role": role,
                        "content": [{"text": content}]
                    })
            
            # Ensure conversation starts with a user message (Bedrock requirement)
            if not conversation:
                conversation = [{"role": "user", "content": [{"text": "Hello"}]}]
            
            kwargs = dict(
                modelId=self.settings.NOVA_LLM_MODEL,
                messages=conversation,
                inferenceConfig={
                    "maxTokens": max_tokens,
                    "temperature": temperature,
                }
            )
            if system_prompt:
                kwargs["system"] = system_prompt
            
            response = self.nova_client.converse(**kwargs)
            return response["output"]["message"]["content"][0]["text"]
        
        return await _call_nova()
    
    def _messages_to_prompt(self, messages: List[Dict[str, str]]) -> str:
        """Convert chat messages to single prompt for Gemini"""
        prompt_parts = []
        for msg in messages:
            role = msg.get('role', 'user')
            content = msg.get('content', '')
            if role == 'system':
                prompt_parts.append(f"System: {content}")
            elif role == 'user':
                prompt_parts.append(f"User: {content}")
            elif role == 'assistant':
                prompt_parts.append(f"Assistant: {content}")
        return "\n\n".join(prompt_parts)
    
    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 1000
    ) -> str:
        """Chat completion with LLM"""
        return await self.generate_response(messages, temperature, max_tokens)
    
    async def summarize_text(self, text: str, max_length: int = 200) -> str:
        """Summarize text using LLM"""
        messages = [
            {"role": "system", "content": "You are a helpful assistant that summarizes text."},
            {"role": "user", "content": f"Summarize the following text in {max_length} characters or less: {text}"}
        ]
        
        response = await self.generate_response(messages, temperature=0.3, max_tokens=200)
        return response
    
    async def extract_entities(self, text: str) -> List[Dict[str, str]]:
        """Extract entities from text"""
        messages = [
            {"role": "system", "content": "Extract named entities from the text. Return as JSON with entity type and value."},
            {"role": "user", "content": f"Extract entities from: {text}"}
        ]
        
        response = await self.generate_response(messages, temperature=0.1, max_tokens=500)
        return self._parse_entities(response)
    
    async def classify_intent(self, text: str) -> Dict[str, Any]:
        """Classify user intent"""
        messages = [
            {"role": "system", "content": "Classify the user's intent from the message."},
            {"role": "user", "content": f"Classify intent: {text}"}
        ]
        
        response = await self.generate_response(messages, temperature=0.1, max_tokens=100)
        return {"intent": response, "confidence": 0.9}  # Simplified
    
    def _parse_entities(self, response: str) -> List[Dict[str, str]]:
        """Parse entities from LLM response"""
        # Simplified parsing - in production, use proper JSON parsing
        entities = []
        try:
            # This is a simplified example
            # In production, you'd parse the LLM response properly
            entities.append({"entity": "example", "value": "example"})
        except Exception as e:
            logger.error(f"Error parsing entities: {str(e)}")
        
        return entities
