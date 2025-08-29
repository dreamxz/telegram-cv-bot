import os
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import InputFile

# Ambil token & owner dari Railway Environment
API_TOKEN = os.getenv("API_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID", 0))

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

os.makedirs("downloads", exist_ok=True)
user_files = {}

# ===== MENU =====
@dp.message_handler(commands=["start", "menu"])
async def send_welcome(message: types.Message):
    text = (
        "📂 *Menu Bot CV*\n\n"
        "🔄 File Conversion\n"
        "/cv_txt_to_vcf - Ubah TXT ke VCF\n"
        "/cv_vcf_to_txt - Ubah VCF ke TXT\n\n"
        "🗂 Manage File\n"
        "/merge - Gabungkan file TXT/VCF\n"
        "/split - Pecah file TXT/VCF\n"
        "/renamefile - Ganti nama file hasil\n"
        "/addctc - Tambahkan nomor ke file terakhir\n"
        "/delctc - Hapus nomor dari file terakhir\n"
        "/to_txt - Ubah teks jadi file .txt\n\n"
        "⚙️ Tools\n"
        "/reset - Reset data sementara\n"
        "/laporkanbug - Lapor bug ke admin\n"
    )
    await message.reply(text, parse_mode="Markdown")

# ===== RESET =====
@dp.message_handler(commands=["reset"])
async def reset_user(message: types.Message):
    user_files[message.from_user.id] = []
    await message.reply("✅ Data sementara berhasil direset.")

# ===== MERGE =====
@dp.message_handler(commands=["merge"])
async def merge_files(message: types.Message):
    user_files[message.from_user.id] = []
    await message.reply("📤 Kirim beberapa file `.txt` atau `.vcf`. Setelah selesai, ketik /done")

@dp.message_handler(commands=["done"])
async def process_merge(message: types.Message):
    files = user_files.get(message.from_user.id, [])
    if not files:
        await message.reply("⚠️ Tidak ada file untuk digabung.")
        return

    ext = os.path.splitext(files[0])[1]
    merged_file = f"downloads/merged{ext}"

    with open(merged_file, "w") as outfile:
        for fname in files:
            with open(fname, "r") as infile:
                outfile.write(infile.read() + "\n")

    await message.reply_document(InputFile(merged_file))
    for f in files:
        os.remove(f)
    os.remove(merged_file)
    user_files[message.from_user.id] = []

# ===== SPLIT =====
@dp.message_handler(commands=["split"])
async def split_file(message: types.Message):
    await message.reply("📤 Kirim file `.txt` atau `.vcf` untuk dipisah (50 baris per file).")

# ===== ADD CONTACT =====
@dp.message_handler(commands=["addctc"])
async def add_contact(message: types.Message):
    await message.reply("✏️ Ketik nomor yang mau ditambahkan. Contoh:\n`/addctc 6281234567890`", parse_mode="Markdown")

@dp.message_handler(commands=lambda msg: msg.text and msg.text.startswith("/addctc "))
async def process_add_contact(message: types.Message):
    num = message.text.replace("/addctc ", "").strip()
    if not os.path.exists("downloads/lastfile"):
        await message.reply("⚠️ Belum ada file terakhir.")
        return
    with open("downloads/lastfile", "a") as f:
        f.write(f"{num}\n")
    await message.reply(f"✅ Nomor {num} berhasil ditambahkan!")

# ===== DELETE CONTACT =====
@dp.message_handler(commands=["delctc"])
async def del_contact(message: types.Message):
    await message.reply("✏️ Ketik nomor yang mau dihapus. Contoh:\n`/delctc 6281234567890`", parse_mode="Markdown")

@dp.message_handler(commands=lambda msg: msg.text and msg.text.startswith("/delctc "))
async def process_del_contact(message: types.Message):
    num = message.text.replace("/delctc ", "").strip()
    if not os.path.exists("downloads/lastfile"):
        await message.reply("⚠️ Belum ada file terakhir.")
        return
    with open("downloads/lastfile", "r") as f:
        lines = f.readlines()
    new_lines = [line for line in lines if num not in line]
    with open("downloads/lastfile", "w") as f:
        f.writelines(new_lines)
    await message.reply(f"✅ Nomor {num} berhasil dihapus!")

# ===== TEXT ➝ TXT FILE =====
@dp.message_handler(commands=["to_txt"])
async def to_txt(message: types.Message):
    text = message.get_args()
    if not text:
        await message.reply("⚠️ Gunakan: `/to_txt isi teks`", parse_mode="Markdown")
        return
    filepath = "downloads/text_output.txt"
    with open(filepath, "w") as f:
        f.write(text)
    await message.reply_document(InputFile(filepath))
    os.remove(filepath)

# ===== REPORT BUG =====
@dp.message_handler(commands=["laporkanbug"])
async def report_bug(message: types.Message):
    bug_text = message.get_args()
    if not bug_text:
        await message.reply("⚠️ Gunakan: `/laporkanbug isi laporan`", parse_mode="Markdown")
        return
    if OWNER_ID:
        await bot.send_message(OWNER_ID, f"🐞 Bug dari @{message.from_user.username}:\n{bug_text}")
    await message.reply("✅ Laporan bug sudah dikirim ke admin!")

# ===== HANDLE FILE =====
@dp.message_handler(content_types=["document"])
async def handle_file(message: types.Message):
    file = await message.document.get_file()
    filename = message.document.file_name
    file_path = f"downloads/{filename}"
    await message.document.download(destination_file=file_path)

    # simpan untuk merge
    if message.from_user.id in user_files:
        user_files[message.from_user.id].append(file_path)

    # simpan sebagai lastfile
    os.rename(file_path, "downloads/lastfile")
    file_path = "downloads/lastfile"

    if filename.endswith(".txt"):
        # TXT ➝ VCF
        vcf_file = file_path + ".vcf"
        with open(file_path, "r") as f:
            numbers = f.read().splitlines()
        with open(vcf_file, "w") as f:
            for i, num in enumerate(numbers, start=1):
                f.write("BEGIN:VCARD\nVERSION:3.0\n")
                f.write(f"N:;Contact {i};;;\n")
                f.write(f"FN:Contact {i}\n")
                f.write(f"TEL;TYPE=CELL:{num}\nEND:VCARD\n")
        await message.reply_document(InputFile(vcf_file))
        os.remove(vcf_file)

    elif filename.endswith(".vcf"):
        # VCF ➝ TXT
        txt_file = file_path + ".txt"
        with open(file_path, "r") as f:
            lines = f.readlines()
        numbers = [line.split(":")[-1].strip() for line in lines if line.startswith("TEL")]
        with open(txt_file, "w") as f:
            f.write("\n".join(numbers))
        await message.reply_document(InputFile(txt_file))
        os.remove(txt_file)

    else:
        await message.reply("⚠️ Format file tidak dikenali. Gunakan .txt atau .vcf")

# ===== RUN =====
if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
