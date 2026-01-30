"""Multi-language support service for detection and translation."""
from typing import Optional, Tuple, Dict, List
from langdetect import detect, detect_langs, LangDetectException
from backend.utils.logger import logger

# Language code to name mapping
LANGUAGE_NAMES = {
    'en': 'English',
    'hi': 'Hindi',
    'es': 'Spanish',
    'fr': 'French',
    'de': 'German',
    'zh-cn': 'Chinese (Simplified)',
    'zh-tw': 'Chinese (Traditional)',
    'ja': 'Japanese',
    'ko': 'Korean',
    'ar': 'Arabic',
    'ru': 'Russian',
    'pt': 'Portuguese',
    'it': 'Italian',
    'nl': 'Dutch',
    'pl': 'Polish',
    'tr': 'Turkish',
    'vi': 'Vietnamese',
    'th': 'Thai',
    'id': 'Indonesian',
    'ms': 'Malay',
    'bn': 'Bengali',
    'ta': 'Tamil',
    'te': 'Telugu',
    'mr': 'Marathi',
    'gu': 'Gujarati',
    'kn': 'Kannada',
    'ml': 'Malayalam',
    'pa': 'Punjabi',
    'ur': 'Urdu',
}

# Language flags/emojis
LANGUAGE_FLAGS = {
    'en': '🇬🇧',
    'hi': '🇮🇳',
    'es': '🇪🇸',
    'fr': '🇫🇷',
    'de': '🇩🇪',
    'zh-cn': '🇨🇳',
    'zh-tw': '🇹🇼',
    'ja': '🇯🇵',
    'ko': '🇰🇷',
    'ar': '🇸🇦',
    'ru': '🇷🇺',
    'pt': '🇵🇹',
    'it': '🇮🇹',
    'nl': '🇳🇱',
    'bn': '🇧🇩',
    'ta': '🇮🇳',
    'te': '🇮🇳',
    'mr': '🇮🇳',
    'gu': '🇮🇳',
}


class LanguageService:
    """Handles language detection and translation for multi-lingual RAG."""
    
    def __init__(self):
        self.translator = None
        self._init_translator()
    
    def _init_translator(self):
        """Initialize the Google Translator."""
        try:
            # Try to import googletrans (may fail on Python 3.13+)
            from googletrans import Translator
            self.translator = Translator()
            logger.logger.info("Translation service initialized successfully")
        except (ImportError, ModuleNotFoundError) as e:
            logger.logger.warning(f"Translation service unavailable (googletrans not compatible): {e}")
            logger.logger.info("Cross-lingual search will work with embedding-based semantic matching only")
            self.translator = None
        except Exception as e:
            logger.logger.warning(f"Translation service initialization failed: {e}")
            self.translator = None
    
    def detect_language(self, text: str) -> Tuple[str, float]:
        """
        Detect the language of the given text.
        
        Returns:
            Tuple of (language_code, confidence)
        """
        if not text or len(text.strip()) < 10:
            return 'en', 0.0  # Default to English for very short text
        
        try:
            # Get language probabilities
            langs = detect_langs(text[:1000])  # Use first 1000 chars for efficiency
            
            if langs:
                top_lang = langs[0]
                return str(top_lang.lang), top_lang.prob
            
            # Fallback to simple detection
            lang = detect(text[:1000])
            return lang, 0.8
            
        except LangDetectException as e:
            logger.logger.debug(f"Language detection failed: {e}")
            return 'en', 0.0
        except Exception as e:
            logger.logger.error(f"Language detection error: {e}")
            return 'en', 0.0
    
    def get_language_name(self, code: str) -> str:
        """Get the human-readable name for a language code."""
        return LANGUAGE_NAMES.get(code, code.upper())
    
    def get_language_flag(self, code: str) -> str:
        """Get the flag emoji for a language code."""
        return LANGUAGE_FLAGS.get(code, '🌐')
    
    def translate(self, text: str, source_lang: str = 'auto', target_lang: str = 'en') -> Optional[str]:
        """
        Translate text from source language to target language.
        
        Args:
            text: Text to translate
            source_lang: Source language code (or 'auto' for detection)
            target_lang: Target language code
            
        Returns:
            Translated text or None if translation failed
        """
        if not self.translator:
            logger.logger.warning("Translator not available")
            return None
        
        if not text or len(text.strip()) < 3:
            return text
        
        # Don't translate if source and target are the same
        if source_lang != 'auto' and source_lang == target_lang:
            return text
        
        try:
            result = self.translator.translate(
                text[:5000],  # Limit text length
                src=source_lang if source_lang != 'auto' else None,
                dest=target_lang
            )
            return result.text
        except Exception as e:
            logger.logger.error(f"Translation failed: {e}")
            return None
    
    def translate_query_to_languages(self, query: str, target_languages: List[str]) -> Dict[str, str]:
        """
        Translate a query to multiple target languages for cross-lingual search.
        
        Args:
            query: The search query
            target_languages: List of language codes to translate to
            
        Returns:
            Dictionary mapping language codes to translated queries
        """
        translations = {'original': query}
        
        # Detect source language
        source_lang, _ = self.detect_language(query)
        translations['detected_language'] = source_lang
        
        if not self.translator:
            return translations
        
        for lang in target_languages:
            if lang != source_lang:
                translated = self.translate(query, source_lang, lang)
                if translated:
                    translations[lang] = translated
        
        return translations
    
    def get_multilingual_query_embeddings(self, query: str, embedding_manager) -> List[Tuple[str, List[float]]]:
        """
        Generate embeddings for query in multiple languages.
        
        Returns:
            List of (language_code, embedding) tuples
        """
        embeddings = []
        
        # Get original query embedding
        original_embedding = embedding_manager.embed_text(query)
        if original_embedding:
            source_lang, _ = self.detect_language(query)
            embeddings.append((source_lang, original_embedding))
        
        # Translate to common languages and get embeddings
        common_languages = ['en', 'hi']  # English and Hindi for cross-lingual
        
        for lang in common_languages:
            translated = self.translate(query, 'auto', lang)
            if translated and translated != query:
                translated_embedding = embedding_manager.embed_text(translated)
                if translated_embedding:
                    embeddings.append((lang, translated_embedding))
        
        return embeddings


# Global instance
language_service = LanguageService()


def detect_language(text: str) -> Tuple[str, float]:
    """Convenience function for language detection."""
    return language_service.detect_language(text)


def translate_text(text: str, source: str = 'auto', target: str = 'en') -> Optional[str]:
    """Convenience function for translation."""
    return language_service.translate(text, source, target)


def get_language_info(code: str) -> Dict[str, str]:
    """Get full language info for a code."""
    return {
        'code': code,
        'name': language_service.get_language_name(code),
        'flag': language_service.get_language_flag(code)
    }
