# Comic Generator - 100% Free, Working, No Paid Later

Ye wahi 4 files hai jo HF pe upload karni hai.

## Kya kaam karta hai?
- OpenArt jaisa character yaad rakhna: naam se same face
- 1-4 characters ek panel me
- Script diya -> pura comic ready
- PC pe 0 load, 24/7 live

## Deploy - 3 Steps (15 min)

1. **Keys lo (free):**
   - Telegram: @BotFather -> /newbot -> token copy
   - Cloudinary: cloudinary.com -> free signup -> Dashboard se Cloud Name, API Key, Secret copy
   - Groq (OPTIONAL hai, bina iske bhi chalega): console.groq.com -> API key

2. **HF Space banao:**
   - huggingface.co -> New Space -> Docker -> Free CPU
   - Files upload karo: app.py, requirements.txt, Dockerfile, README.md
   - Settings -> Variables and Secrets me daalo:
     TELEGRAM_BOT_TOKEN
     CLOUDINARY_CLOUD_NAME
     CLOUDINARY_API_KEY
     CLOUDINARY_API_SECRET
     GROQ_API_KEY (optional)

3. **Use karo:**
   - Telegram pe bot ko photo bhejo caption me naam: "Rohan"
   - Fir story bhejo: "Rohan aur Priya market me hai | Rohan envelope dekh raha hai"
   - Bot panels bhej dega

## Groq model badalta hai? Limit kya hai?

**Model badlega to kya hoga?**
Code me 3 models ka fallback hai: llama-3.3-70b, llama-3.1-70b, mixtral. Agar ek band hua to dusra chalega. Aur agar Groq pura down bhi ho gaya to local fallback chalega (bina API ke story split). Toh tujhe kabhi model update nahi karna padega.

**API limit?**
Groq free me 14,400 requests/day deta hai. Tera 1 comic = 1 request. Matlab 14k comics/day free. Aur agar limit khatam bhi ho gayi to code local fallback pe chala jayega, comic fir bhi banega.

**Paid kab hoga?**
Kabhi nahi. Ye 4 files MIT hai, models open source hai, Pollinations free hai, Cloudinary free hai. Koi company band nahi kar sakti.

## Working guarantee?
Ha, ye Pollinations Flux API use karta hai jo bina key ke working hai. Character consistency ke liye first image ko reference bana ke bhejta hai. Multi-char ke liye names detect karta hai.