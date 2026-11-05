import os, re, requests, threading, asyncio, random
from io import BytesIO
import cloudinary
import cloudinary.uploader
from flask import Flask
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET")
)

CHAR_DB = {}

flask_app = Flask(__name__)

@flask_app.route('/')
def home():
    return "Comic Bot Strong SDXL - Running! Go to Telegram"

@flask_app.route('/health')
def health():
    return "OK"

try:
    from groq import Groq
    groq_client = Groq(api_key=os.getenv("GROQ_API_KEY")) if os.getenv("GROQ_API_KEY") else None
except:
    groq_client = None

def split_script_to_panels(script_text):
    if groq_client:
        try:
            models_to_try = ["llama-3.3-70b-versatile", "llama-3.1-70b-versatile", "mixtral-8x7b-32768"]
            for model_name in models_to_try:
                try:
                    prompt = f"Split this story into 3-5 comic panels. Each panel one sentence with character names. Story: {script_text}. Return only numbered list like 1. ... 2. ..."
                    res = groq_client.chat.completions.create(model=model_name, messages=[{"role":"user","content":prompt}])
                    text = res.choices[0].message.content
                    panels = re.findall(r'\d+\.\s*(.*)', text)
                    if panels:
                        return panels[:5]
                except:
                    continue
        except:
            pass
    if "|" in script_text:
        panels = [p.strip() for p in script_text.split("|") if p.strip()]
    else:
        panels = [p.strip() for p in re.split(r'[\.\n]+', script_text) if p.strip()]
    return panels[:5] if panels else [script_text]

def build_strong_prompt(base_prompt):
    """Build strong prompt with gender enforcement"""
    lower = base_prompt.lower()
    
    # Gender detection
    is_male = any(w in lower for w in ["male", "boy", "man", "hero", "he ", "his", "rohan", "aman", "male"])
    is_female = any(w in lower for w in ["female", "girl", "woman", "she ", "her", "priya", "female"])
    
    # If male asked but female words not present, enforce male
    if is_male and not is_female:
        strong = f"{base_prompt}, male man, masculine, male superhero, strong male character, beard optional"
        negative = "female, woman, girl, female face, long hair female, makeup, lipstick"
    elif is_female and not is_male:
        strong = f"{base_prompt}, female woman, feminine, female character, beautiful female"
        negative = "male, man, boy, beard, mustache, male face"
    else:
        strong = base_prompt
        negative = ""
    
    # Add comic style enforcement
    strong += ", comic book style, detailed, sharp focus, high quality, 4k, comic panel"
    
    return strong, negative

def generate_image_strong(prompt, character_urls):
    """Strong SDXL with fallbacks - handles 402 and gender"""
    import urllib.parse
    
    strong_prompt, negative_prompt = build_strong_prompt(prompt)
    
    # Try multiple free endpoints with fallback
    endpoints = [
        # Pollinations Flux - primary
        {
            "url": f"https://image.pollinations.ai/prompt/{urllib.parse.quote(strong_prompt)}",
            "params": {
                "model": "flux",
                "width": "1024",
                "height": "1024",
                "nologo": "true",
                "seed": str(random.randint(0, 1000000))
            }
        },
        # Pollinations Turbo - fallback 1 (better for male/female)
        {
            "url": f"https://image.pollinations.ai/prompt/{urllib.parse.quote(strong_prompt)}",
            "params": {
                "model": "turbo",
                "width": "1024",
                "height": "1024",
                "nologo": "true",
                "seed": str(random.randint(0, 1000000))
            }
        },
        # Without model param - fallback 2
        {
            "url": f"https://image.pollinations.ai/prompt/{urllib.parse.quote(strong_prompt)}",
            "params": {
                "width": "1024",
                "height": "1024",
                "nologo": "true"
            }
        }
    ]
    
    # Add reference image if available
    if character_urls:
        ref = character_urls[0]
        if ref.startswith("http"):
            for ep in endpoints:
                ep["params"]["image"] = ref
    
    last_error = None
    for ep in endpoints:
        try:
            print(f"Trying endpoint: {ep['url']} with params {ep['params']}")
            r = requests.get(ep["url"], params=ep["params"], timeout=120)
            if r.status_code == 402:
                print(f"402 Payment Required, trying next endpoint")
                last_error = "402"
                continue
            r.raise_for_status()
            # Check if response is image
            if 'image' in r.headers.get('Content-Type', '') or len(r.content) > 10000:
                return r.content
            else:
                last_error = "Not image"
                continue
        except Exception as e:
            print(f"Endpoint failed: {e}")
            last_error = str(e)
            continue
    
    # Final fallback - generate without reference and with simpler prompt
    try:
        simple_url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(prompt)}?width=1024&height=1024&nologo=true"
        r = requests.get(simple_url, timeout=60)
        r.raise_for_status()
        return r.content
    except Exception as e:
        raise Exception(f"All endpoints failed. Last error: {last_error}. Original error: {e}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Comic Bot Strong SDXL Live hai ✅\n"
        "Ab gender bhi sahi samjhega!\n"
        "1. Photo bhejo caption me naam likh ke (jaise: Rohan)\n"
        "2. Fir story bhejo, jaise: male superhero barish me hai | male hero udd raha hai\n"
        "Bot male/female sahi dega, 1-4 characters ek panel me."
    )

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    caption = (update.message.caption or "").strip()
    if not caption:
        await update.message.reply_text("Caption me naam likho jaise: Rohan")
        return
    photo_file = await update.message.photo[-1].get_file()
    photo_bytes = await photo_file.download_as_bytearray()
    try:
        upload = cloudinary.uploader.upload(BytesIO(photo_bytes), folder="comic_chars", public_id=caption.lower(), overwrite=True)
        url = upload['secure_url']
        CHAR_DB[caption.lower()] = url
        await update.message.reply_text(f"Saved: {caption} -> {url}\nAb story bhejo. Male ke liye 'male' word likho jaise 'male superhero'")
    except Exception as e:
        CHAR_DB[caption.lower()] = f"local_{caption.lower()}"
        await update.message.reply_text(f"Saved locally: {caption}. Error: {e}")

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    script = update.message.text
    if script.startswith("/"):
        return
    panels = split_script_to_panels(script)
    await update.message.reply_text(f"Script ko {len(panels)} panels me toda. Strong SDXL se generate kar raha hu (gender fix ke saath)...")
    for i, panel_prompt in enumerate(panels, 1):
        found_chars = [name for name in CHAR_DB.keys() if name.lower() in panel_prompt.lower()]
        urls = [CHAR_DB[n] for n in found_chars if not n.startswith("local_")]
        try:
            img_bytes = generate_image_strong(panel_prompt, urls)
            await update.message.reply_photo(
                photo=BytesIO(img_bytes),
                caption=f"Panel {i}/{len(panels)}: {panel_prompt} | Chars: {', '.join(found_chars) if found_chars else 'No ref - generic'}"
            )
        except Exception as e:
            await update.message.reply_text(f"Panel {i} fail: {e}\nRetrying with simpler prompt...")
            try:
                # Retry with very simple prompt
                simple_bytes = generate_image_strong(f"comic {panel_prompt}", [])
                await update.message.reply_photo(
                    photo=BytesIO(simple_bytes),
                    caption=f"Panel {i} (retry): {panel_prompt}"
                )
            except Exception as e2:
                await update.message.reply_text(f"Panel {i} final fail: {e2}")

def run_flask():
    port = int(os.getenv("PORT", 10000))
    print(f"Starting Flask on port {port}...")
    flask_app.run(host="0.0.0.0", port=port)

def run_telegram_bot():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    if not TELEGRAM_TOKEN:
        print("ERROR: TELEGRAM_BOT_TOKEN missing")
        return
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    print("Bot starting polling - Strong SDXL version...")
    app.run_polling()

if __name__ == "__main__":
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    run_telegram_bot()
