# 🌍 Quick Start: Using Auto-Translate

## What is Auto-Translate?

Auto-Translate allows you to **ask questions in your native language** and get **answers in that same language**, even when your documents are in English (or any other language).

---

## ⚡ Quick Example

### Before (English Only)
```
You: "How does this machine work?"
System: "This machine operates in three steps..."
```

### After (Any Language!)
```
You (Hindi): "यह मशीन कैसे काम करती है?"
System (Hindi): "यह मशीन तीन चरणों में काम करती है..."

You (Spanish): "¿Cómo funciona esta máquina?"
System (Spanish): "Esta máquina funciona en tres pasos..."

You (French): "Comment fonctionne cette machine?"
System (French): "Cette machine fonctionne en trois étapes..."
```

---

## 🚀 How to Use

### Step 1: Upload Documents (Any Language)
Upload your documents as usual. They can be in any language, but typically English.

### Step 2: Ask in Your Language
Simply type your question in **your preferred language**. The system will:
1. 🔍 **Detect** what language you're using
2. 🔄 **Translate** your question to English (if needed)
3. 📚 **Search** the English knowledge base
4. 💬 **Generate** an answer in English
5. 🔄 **Translate back** to your language
6. ✅ **Deliver** the answer in your native language!

### Step 3: Read the Answer
The answer comes back in **your language**, with all the same features:
- ✅ Source citations
- ✅ Confidence scores
- ✅ Conflict detection
- ✅ Reasoning chains

---

## 🌐 Supported Languages

The system supports **30+ languages** including:

### Indian Languages 🇮🇳
- Hindi (हिन्दी)
- Bengali (বাংলা)
- Tamil (தமிழ்)
- Telugu (తెలుగు)
- Marathi (मराठी)
- Gujarati (ગુજરાતી)
- Kannada (ಕನ್ನಡ)
- Malayalam (മലയാളം)
- Punjabi (ਪੰਜਾਬੀ)
- Urdu (اردو)

### European Languages
- Spanish 🇪🇸
- French 🇫🇷
- German 🇩🇪
- Italian 🇮🇹
- Portuguese 🇵🇹
- Dutch 🇳🇱
- Polish
- Russian 🇷🇺
- Turkish

### Asian Languages
- Chinese (Simplified) 🇨🇳
- Chinese (Traditional) 🇹🇼
- Japanese 🇯🇵
- Korean 🇰🇷
- Arabic 🇦🇪
- Vietnamese
- Thai
- Indonesian
- Malay

---

## 📝 Example Questions

### Technical Questions
```
English:   "How do I reset the machine?"
Hindi:     "मैं मशीन को कैसे रीसेट करूं?"
Spanish:   "¿Cómo reseteo la máquina?"
French:    "Comment réinitialiser la machine?"
Japanese:  "マシンをリセットするには？"
```

### Information Queries
```
English:   "What are the safety features?"
Hindi:     "सुरक्षा विशेषताएं क्या हैं?"
Spanish:   "¿Cuáles son las características de seguridad?"
Arabic:    "ما هي ميزات السلامة؟"
```

### Troubleshooting
```
English:   "Why won't the machine start?"
Hindi:     "मशीन क्यों नहीं चालू हो रही है?"
German:    "Warum startet die Maschine nicht?"
Korean:    "기계가 왜 작동하지 않습니까?"
```

---

## 🔧 API Usage

### Enable Auto-Translate (Default)
```json
POST /query
{
  "query": "यह मशीन कैसे काम करती है?",
  "enable_auto_translate": true
}
```

### Check Translation Info in Response
```json
{
  "query": "यह मशीन कैसे काम करती है?",
  "answer": "यह मशीन तीन चरणों में काम करती है...",
  "translation_info": {
    "detected_language": "hi",
    "detected_language_name": "Hindi",
    "detected_language_flag": "🇮🇳",
    "needs_translation": true,
    "original_query": "यह मशीन कैसे काम करती है?",
    "translated_query": "How does this machine work?",
    "response_translated": true
  }
}
```

### Disable Auto-Translate (If Needed)
```json
POST /query
{
  "query": "यह मशीन कैसे काम करती है?",
  "enable_auto_translate": false
}
```

---

## 💡 Tips & Best Practices

### ✅ DO
- Write clear, complete questions
- Use proper grammar in your language
- Include context when needed
- Check the translation_info to verify detection

### ❌ DON'T
- Mix multiple languages in one query
- Use very short queries (detection needs context)
- Expect code or technical terms to translate perfectly
- Worry if translation takes a bit longer

---

## 🎯 Real-World Use Cases

### 1. Customer Support (Multilingual)
```
Documents: English product manuals
Users: Ask in Hindi, Spanish, French, etc.
Result: Everyone gets answers in their language!
```

### 2. Education
```
Documents: English textbooks
Students: Study in their native language
Result: Better comprehension and learning
```

### 3. Technical Documentation
```
Documents: English technical specs
Engineers: Access in local language
Result: Faster troubleshooting
```

### 4. Medical Information
```
Documents: English medical journals
Practitioners: Read in local language
Result: Better patient care
```

---

## 🐛 Troubleshooting

### "My language wasn't detected correctly"
- **Solution**: Make sure your query is at least 10-15 characters long
- **Why**: Short queries don't have enough context for accurate detection

### "Translation seems off"
- **Solution**: Try rephrasing your question more clearly
- **Why**: Translation works best with grammatically correct sentences

### "Response is still in English"
- **Check**: Is `enable_auto_translate: true` in your request?
- **Check**: Look at the `translation_info.needs_translation` value
- **Note**: English queries won't be translated (they're already English!)

### "Translation is slow"
- **Normal**: Translation adds 300-500ms to query time
- **Tip**: First-time queries may be slower due to model loading

---

## 🎓 Testing the Feature

### Quick Test Script
```bash
# From the project root
python test_auto_translate.py
```

This will:
- ✅ Test queries in 5+ languages
- ✅ Verify detection accuracy
- ✅ Check translation quality
- ✅ Display detailed results

### Manual Testing
1. Start the server: `python start.ps1`
2. Upload the example manual: `machine_manual_example.txt`
3. Open the UI: `http://localhost:8000`
4. Try these queries:
   - Hindi: `यह मशीन कैसे काम करती है?`
   - Spanish: `¿Cómo funciona esta máquina?`
   - French: `Comment fonctionne cette machine?`

---

## 📚 Learn More

- **Full Documentation**: [AUTO_TRANSLATE_FEATURE.md](AUTO_TRANSLATE_FEATURE.md)
- **Language Service**: [backend/utils/language_service.py](backend/utils/language_service.py)
- **API Models**: [backend/models/query.py](backend/models/query.py)

---

## 🌟 Summary

### In 3 Steps:
1. **Upload** documents (usually English)
2. **Ask** in any language
3. **Get** answers in that language!

### Benefits:
- ✅ Ask in 30+ languages
- ✅ No duplicate documents needed
- ✅ Same great RAG features
- ✅ Full transparency with translation metadata

**Start asking in your language today!** 🌍✨

---

**Questions?** Check [AUTO_TRANSLATE_FEATURE.md](AUTO_TRANSLATE_FEATURE.md) for detailed documentation.
