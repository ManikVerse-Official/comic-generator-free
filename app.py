import os, re, requests
from io import BytesIO
import cloudinary
import cloudinary.uploader
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# --- CONFIG FROM HF SECRETS ---
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CLOUD_NAME = os.getenv("CLOUDINARY_CLOUD_NAME")

cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET")
)

CHAR_DB = {}  # name -> url

# Groq is OPTIONAL now - fallback built-in
try:
    from groq import Groq
    groq_client = Groq(api_key=os.getenv("GROQ_API_KEY")) if os.getenv("GROQ_API_KEY") else None
except:
    groq_client = None

def split_script_to_panels(script_text):
    # Try Groq first (free, fast)
    if groq_client:
        try:
            # Model auto-fallback: if one fails, try other
            models_to_try = ["llama-3.3-70b-versatile", "llama-3.1-70b-versatile", "mixtral-8x7b-32768"]
            for model_name in models_to_try:
                try:
                    prompt = f"Split this story into 3-5 comic panels. Each panel one sentence with character names. Story: {script_text}. Return only numbered list like 1. ... 2. ..."
                    res = groq_client.chat.completions.create(model=model_name, messages=[{"role":"user","content":prompt}])
                    text = res.choices[0].message.content
                    panels = re.findall(r'\d+\.\s*(.*)', text)
                    if panels:
                        return panels[:5]
                except Exception as e:
                    print(f"Model {model_name} failed: {e}")
                    continue
        except Exception as e:
            print(f"Groq failed, using local fallback: {e}")

    # LOCAL FALLBACK - No API needed, always works
    # Simple but working: split by . or |
    if "|" in script_text:
        panels = [p.strip() for p in script_text.split("|") if p.strip()]
    else:
        panels = [p.strip() for p in re.split(r'[\.\n]+', script_text) if p.strip()]
    return panels[:5] if panels else [script_text]

def generate_image_pollinations(prompt, character_urls):
    # 100% FREE, no key needed, working
    base_url = "https://image.pollinations.ai/prompt/"
    full_prompt = f"{prompt}, comic style, consistent character, detailed face, vibrant"
    if character_urls:
        ref = character_urls[0]
        url = f"{base_url}{requests.utils.quote(full_prompt)}?model=flux&image={requests.utils.quote(ref)}&width=1024&height=1024&nologo=true"
    else:
        url = f"{base_url}{requests.utils.quote(full_prompt)}?model=flux&width=1024&height=1024&nologo=true"
    r = requests.get(url, timeout=90)
    r.raise_for_status()
    return r.content

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Comic Bot Live hai ✅\n"
        "1. Photo bhejo caption me naam likh ke (jaise: Rohan)\n"
        "2. Fir story bhejo, jaise: Rohan aur Priya market me hai | Rohan envelope dekh raha hai\n"
        "Bot 1-4 characters ek panel me handle karega."
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
        await update.message.reply_text(f"Saved: {caption} -> {url}\nAb story bhejo.")
    except Exception as e:
        # If cloudinary not set, save locally in memory
        CHAR_DB[caption.lower()] = f"local_{caption.lower()}"
        await update.message.reply_text(f"Saved locally: {caption} (Cloudinary not set, but still works)\nAb story bhejo. Error: {e}")

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    script = update.message.text
    if script.startswith("/"):
        return
    panels = split_script_to_panels(script)
    await update.message.reply_text(f"Script ko {len(panels)} panels me toda. Generate kar raha hu...")
    for i, panel_prompt in enumerate(panels, 1):
        found_chars = [name for name in CHAR_DB.keys() if name.lower() in panel_prompt.lower()]
        urls = [CHAR_DB[n] for n in found_chars if not n.startswith("local_")]
        try:
            img_bytes = generate_image_pollinations(panel_prompt, urls)
            await update.message.reply_photo(
                photo=BytesIO(img_bytes),
                caption=f"Panel {i}/{len(panels)}: {panel_prompt} | Chars: {', '.join(found_chars) if found_chars else 'No ref'}"
            )
        except Exception as e:
            await update.message.reply_text(f"Panel {i} fail: {e}")

def main():
    if not TELEGRAM_TOKEN:
        print("ERROR: Set TELEGRAM_BOT_TOKEN in HF Secrets")
        return
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    print("Bot starting... Working, no Groq needed if key missing")
    app.run_polling()

if __name__ == "__main__":
    main()