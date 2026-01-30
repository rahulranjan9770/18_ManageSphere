"""
Test script for Auto-Translate Knowledge Base feature.

This script demonstrates the multilingual query capabilities:
1. Ask questions in different languages
2. Get answers in those same languages
3. Verify translation transparency
"""

import requests
import json
from typing import Dict, Any

# API endpoint
BASE_URL = "http://localhost:8000"

def test_query(query: str, language_name: str, enable_auto_translate: bool = True) -> Dict[str, Any]:
    """
    Send a test query and display the results.
    
    Args:
        query: The question to ask
        language_name: Name of the language for display
        enable_auto_translate: Whether to enable auto-translation
    """
    print(f"\n{'='*80}")
    print(f"🌍 Testing {language_name} Query")
    print(f"{'='*80}")
    print(f"Query: {query}")
    print(f"Auto-translate: {'Enabled' if enable_auto_translate else 'Disabled'}")
    print(f"{'-'*80}")
    
    # Make request
    response = requests.post(
        f"{BASE_URL}/query",
        json={
            "query": query,
            "enable_auto_translate": enable_auto_translate,
            "include_reasoning_chain": True,
            "persona": "standard"
        }
    )
    
    if response.status_code != 200:
        print(f"❌ Error: {response.status_code}")
        print(response.text)
        return None
    
    data = response.json()
    
    # Display results
    print(f"\n📝 Response:")
    print(f"{data.get('answer', 'No answer')[:300]}...")
    
    print(f"\n📊 Confidence: {data.get('confidence')} ({data.get('confidence_score', 0):.2f})")
    print(f"⏱️  Processing Time: {data.get('processing_time', 0):.2f}s")
    
    # Display translation info
    trans_info = data.get('translation_info')
    if trans_info:
        print(f"\n🌐 Translation Info:")
        print(f"   Detected Language: {trans_info.get('detected_language_flag', '')} "
              f"{trans_info.get('detected_language_name', 'Unknown')} "
              f"(Confidence: {trans_info.get('confidence', 0):.2f})")
        
        if trans_info.get('needs_translation'):
            print(f"   ✅ Translation Enabled")
            print(f"   Original Query: {trans_info.get('original_query', '')}")
            print(f"   Translated Query: {trans_info.get('translated_query', '')}")
            print(f"   Response Translated: {trans_info.get('response_translated', False)}")
        else:
            print(f"   ℹ️  No translation needed (English query)")
    
    # Display key insights from reasoning chain
    reasoning = data.get('reasoning_chain')
    if reasoning and reasoning.get('key_insights'):
        print(f"\n💡 Key Insights:")
        for insight in reasoning['key_insights'][:5]:
            print(f"   {insight}")
    
    print(f"\n{'='*80}")
    
    return data


def main():
    """Run test queries in different languages."""
    
    print("\n" + "="*80)
    print("🌍 AUTO-TRANSLATE KNOWLEDGE BASE - TEST SUITE")
    print("="*80)
    print("\nThis test demonstrates multilingual query capabilities.")
    print("Make sure your RAG server is running and has English documents uploaded.")
    print("\nNote: First upload some English documents using the UI or API.")
    
    # Test queries in different languages
    test_cases = [
        {
            "query": "How does this machine work?",
            "language": "English (Baseline)",
            "enable_translate": True
        },
        {
            "query": "यह मशीन कैसे काम करती है?",
            "language": "Hindi",
            "enable_translate": True
        },
        {
            "query": "¿Cómo funciona esta máquina?",
            "language": "Spanish",
            "enable_translate": True
        },
        {
            "query": "Comment fonctionne cette machine?",
            "language": "French",
            "enable_translate": True
        },
        {
            "query": "この機械はどのように機能しますか？",
            "language": "Japanese",
            "enable_translate": True
        },
        {
            "query": "यह सिस्टम क्या करता है?",
            "language": "Hindi (2nd test)",
            "enable_translate": True
        }
    ]
    
    results = []
    
    for i, test in enumerate(test_cases, 1):
        try:
            print(f"\n📌 Test {i}/{len(test_cases)}")
            result = test_query(
                query=test["query"],
                language_name=test["language"],
                enable_auto_translate=test["enable_translate"]
            )
            results.append({
                "test": test["language"],
                "success": result is not None,
                "translated": result.get('translation_info', {}).get('needs_translation', False) if result else False
            })
        except Exception as e:
            print(f"❌ Test failed: {e}")
            results.append({
                "test": test["language"],
                "success": False,
                "translated": False
            })
    
    # Summary
    print("\n" + "="*80)
    print("📊 TEST SUMMARY")
    print("="*80)
    
    successful = sum(1 for r in results if r['success'])
    total = len(results)
    
    print(f"\n✅ Successful: {successful}/{total}")
    print(f"❌ Failed: {total - successful}/{total}")
    
    print("\n📋 Detailed Results:")
    for i, result in enumerate(results, 1):
        status = "✅" if result['success'] else "❌"
        trans = "🔄" if result['translated'] else "➡️"
        print(f"   {i}. {status} {trans} {result['test']}")
    
    print("\n" + "="*80)
    print("🎉 Test Complete!")
    print("\nLegend:")
    print("   ✅ = Test passed")
    print("   ❌ = Test failed")
    print("   🔄 = Translation applied")
    print("   ➡️ = No translation (English)")
    print("="*80 + "\n")


if __name__ == "__main__":
    main()
