import http.server
import socketserver
import json
import os
import sys
import re
import urllib.parse

# Force UTF-8 encoding for Windows console
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

PORT = 8085
if len(sys.argv) > 1:
    try:
        PORT = int(sys.argv[1])
    except ValueError:
        pass

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PKKS_FOLDER_NAME = "PKKS 2026"
UPLOADS_DIR = os.path.join(BASE_DIR, PKKS_FOLDER_NAME)

DATA_DIR = os.path.join(BASE_DIR, "data_users")
os.makedirs(UPLOADS_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)

SETTINGS_FILE = os.path.join(DATA_DIR, "settings.json")

INITIAL_USERS = [
  {"id": "abdul_yakub", "name": "Abdul Yakub, S.Ag", "role": "kepsek", "jabatan": "Kepala Sekolah & Evaluator"},
  {"id": "susanti", "name": "Susanti, S.Kom, S.Pd", "role": "guru", "jabatan": "Guru Komputer / TI"},
  {"id": "legina_puspa", "name": "Legina Puspa Wardini,S.Pd.I", "role": "guru", "jabatan": "Guru Kelas"},
  {"id": "bintari_kusumaningsih", "name": "Bintari Kusumaningsih, S.H", "role": "guru", "jabatan": "Guru Kelas"},
  {"id": "ocha_desy", "name": "Ocha Desy Ariyanti, S.Pd", "role": "guru", "jabatan": "Guru Kelas"},
  {"id": "mia_chairunnisa", "name": "Mia Chairunnisa, S.Pd", "role": "guru", "jabatan": "Guru Kelas"},
  {"id": "muhammad_irfan", "name": "Muhammad Irfan, S.Pd", "role": "guru", "jabatan": "Guru Kelas"},
  {"id": "dwi_erlindawati", "name": "Dwi Erlindawati, M.Pd", "role": "guru", "jabatan": "Guru Kelas"},
  {"id": "sherly_mugi", "name": "Sherly Mugi Anugrah, S.E", "role": "guru", "jabatan": "Guru Kelas"},
  {"id": "ita_tegowati", "name": "Ita Tegowati, S.Pd.I", "role": "guru", "jabatan": "Guru PAI"},
  {"id": "liko_ranti", "name": "Liko Ranti, S.Pd", "role": "guru", "jabatan": "Guru Kelas"},
  {"id": "esthy_ening", "name": "N. Esthy Ening S., S.Sos", "role": "guru", "jabatan": "Guru Kelas"},
  {"id": "abdullah", "name": "Abdullah, S.Ag", "role": "guru", "jabatan": "Guru PAI"},
  {"id": "dahlan_setiawan", "name": "Dahlan Setiawan, S.Pd", "role": "guru", "jabatan": "Guru PJOK"},
  {"id": "eko_mulyawan", "name": "Eko Mulyawan, A.Md", "role": "guru", "jabatan": "Guru Kelas"},
  {"id": "abdurohim", "name": "Abdurohim, S.Pd", "role": "guru", "jabatan": "Guru Kelas"},
  {"id": "muhammad_ali_yusuf", "name": "Muhammad Ali Yusuf", "role": "guru", "jabatan": "Guru Kelas"},
  {"id": "yeni_istiyani", "name": "Yeni Istiyani, S.Pd.I", "role": "guru", "jabatan": "Guru Kelas"},
  {"id": "indyah_montisari", "name": "Indyah Montisari", "role": "guru", "jabatan": "Guru Kelas"},
  {"id": "habib_riyadhi", "name": "Habib Riyadhi", "role": "guru", "jabatan": "Guru Kelas"},
  {"id": "rahmat_abdullah", "name": "Rahmat Abdullah", "role": "guru", "jabatan": "Guru Kelas"},
  {"id": "misbah_adeline", "name": "Misbah Adeline, S.E", "role": "guru", "jabatan": "Guru Kelas"},
  {"id": "hidayat", "name": "Hidayat", "role": "guru", "jabatan": "Guru Kelas"},
  {"id": "andi_purnomo", "name": "Andi Purnomo", "role": "guru", "jabatan": "Guru Kelas"},
  {"id": "rayhan", "name": "Rayhan", "role": "guru", "jabatan": "Guru Kelas"},
  {"id": "tio_rumboko", "name": "Tio Rumboko", "role": "guru", "jabatan": "Guru Kelas"},
  {"id": "puji_astuti", "name": "Puji Astuti", "role": "guru", "jabatan": "Guru Kelas"}
]

DEFAULT_SETTINGS = {
  "namaSekolah": "SDIT ANNISA BOGOR",
  "alamatSekolah": "Jl. Raya Ciomas No. 12, Ciomas, Kabupaten Bogor",
  "namaKepalaSekolah": "Abdul Yakub, S.Ag",
  "defaultPassword": "Sditannisa",
  "tanggalCetak": "Bekasi, 29 September 2026",
  "googleDriveLink": "",
  "users": INITIAL_USERS
}

def load_settings():
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for k, v in DEFAULT_SETTINGS.items():
                    if k not in data:
                        data[k] = v
                return data
        except Exception as e:
            print(f"Error reading settings.json: {e}")
    save_settings(DEFAULT_SETTINGS)
    return DEFAULT_SETTINGS

def save_settings(data):
    try:
        with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Error saving settings.json: {e}")

def extract_gdrive_folder_id(url_or_id):
    if not url_or_id:
        return None
    url_or_id = url_or_id.strip()
    if 'folders/' in url_or_id:
        return url_or_id.split('folders/')[1].split('?')[0].split('/')[0]
    elif 'id=' in url_or_id:
        return url_or_id.split('id=')[1].split('&')[0]
    elif len(url_or_id) > 15 and '/' not in url_or_id and '.' not in url_or_id:
        return url_or_id
    return None

def upload_file_to_gdrive_api(file_path, orig_name, user_name, folder_link_or_id):
    creds_file = os.path.join(BASE_DIR, 'credentials.json')
    if not os.path.exists(creds_file):
        creds_file = os.path.join(BASE_DIR, 'service_account.json')
    if not os.path.exists(creds_file):
        return None

    folder_id = extract_gdrive_folder_id(folder_link_or_id)
    if not folder_id:
        return None

    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaFileUpload

        SCOPES = ['https://www.googleapis.com/auth/drive.file', 'https://www.googleapis.com/auth/drive']
        credentials = service_account.Credentials.from_service_account_file(creds_file, scopes=SCOPES)
        service = build('drive', 'v3', credentials=credentials)

        file_metadata = {
            'name': f"[{user_name}] {orig_name}",
            'parents': [folder_id]
        }
        
        ext = os.path.splitext(file_path)[1].lower()
        mime_types = {
            '.pdf': 'application/pdf',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.doc': 'application/msword',
            '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        }
        mime = mime_types.get(ext, 'application/octet-stream')

        media = MediaFileUpload(file_path, mimetype=mime, resumable=True)
        uploaded = service.files().create(body=file_metadata, media_body=media, fields='id, webViewLink, webContentLink').execute()

        try:
            service.permissions().create(fileId=uploaded.get('id'), body={'type': 'anyone', 'role': 'reader'}).execute()
        except Exception as pe:
            print(f"Permission set note: {pe}")

        return uploaded.get('webViewLink') or uploaded.get('webContentLink')
    except Exception as e:
        print(f"GDrive API Upload error: {e}")
        return None

class PKKSRequestHandler(http.server.SimpleHTTPRequestHandler):
    def translate_path(self, path):
        parsed_path = urllib.parse.urlparse(path).path
        unquoted = urllib.parse.unquote(parsed_path)
        if unquoted == '/' or unquoted == '':
            return os.path.join(BASE_DIR, 'index.html')
        if unquoted.startswith('/PKKS 2026/') or unquoted.startswith(f'/{PKKS_FOLDER_NAME}/'):
            rel_path = unquoted.split('/', 2)[-1]
            return os.path.join(UPLOADS_DIR, rel_path)
        if unquoted.startswith('/uploads/'):
            rel_path = unquoted[len('/uploads/'):]
            return os.path.join(UPLOADS_DIR, rel_path)
        return super().translate_path(path)

    def do_GET(self):
        parsed_url = urllib.parse.urlparse(self.path)
        query = urllib.parse.parse_qs(parsed_url.query)

        if parsed_url.path == '/api/pdf-bytes':
            file_name = query.get('file', [''])[0]
            file_name = urllib.parse.unquote(file_name)
            if not file_name:
                self.send_response(400)
                self.end_headers()
                return

            safe_name = os.path.basename(file_name)
            filepath = os.path.join(UPLOADS_DIR, safe_name)

            if os.path.exists(filepath) and os.path.isfile(filepath):
                self.send_response(200)
                # application/octet-stream prevents IDM (Internet Download Manager) from intercepting PDF fetch
                self.send_header('Content-Type', 'application/octet-stream')
                self.send_header('Content-Length', str(os.path.getsize(filepath)))
                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate')
                self.end_headers()
                try:
                    with open(filepath, 'rb') as f:
                        while True:
                            chunk = f.read(65536)
                            if not chunk:
                                break
                            self.wfile.write(chunk)
                except Exception:
                    pass
                return
            else:
                self.send_response(404)
                self.end_headers()
                return

        if parsed_url.path == '/api/settings':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(load_settings(), ensure_ascii=False).encode('utf-8'))
            return

        if parsed_url.path == '/api/users':
            settings = load_settings()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(settings.get('users', []), ensure_ascii=False).encode('utf-8'))
            return

        if parsed_url.path == '/api/data':
            settings = load_settings()
            users = settings.get('users', [])
            user_id = query.get('user', ['abdul_yakub'])[0]
            user_file = os.path.join(DATA_DIR, f"data_{user_id}.json")
            
            user_obj = next((u for u in users if u['id'] == user_id), None)
            user_name = user_obj['name'] if user_obj else user_id

            if os.path.exists(user_file):
                with open(user_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            else:
                data = {
                    "user": user_id,
                    "profile": {
                        "namaSekolah": settings.get('namaSekolah', 'SDIT ANNISA BOGOR'),
                        "alamatSekolah": settings.get('alamatSekolah', ''),
                        "namaGuru": user_name,
                        "namaKepalaSekolah": settings.get('namaKepalaSekolah', 'Abdul Yakub, S.Ag'),
                        "tahunPelajaran": "2025/2026"
                    },
                    "scores": {}
                }

            # Smart Auto-Sync: Scan PKKS 2026 directory for files belonging to this user & clean up deleted files
            if 'scores' not in data:
                data['scores'] = {}

            sanitized_user_prefix = "".join([c for c in user_name if c.isalnum() or c in "_- "]).replace(" ", "_")
            if os.path.exists(UPLOADS_DIR):
                all_disk_files = set(os.listdir(UPLOADS_DIR))

                # 1. Clean up missing/deleted files from data
                for item_id, item_val in data['scores'].items():
                    if isinstance(item_val, dict) and 'uploadedFiles' in item_val:
                        item_val['uploadedFiles'] = [
                            uf for uf in item_val['uploadedFiles']
                            if uf.get('savedName') in all_disk_files or uf.get('name') in all_disk_files or uf.get('isDrive')
                        ]

                # 2. Collect existing file names in data
                known_files = set()
                for item_id, item_val in data['scores'].items():
                    if isinstance(item_val, dict) and 'uploadedFiles' in item_val:
                        for uf in item_val['uploadedFiles']:
                            known_files.add(uf.get('savedName'))
                            known_files.add(uf.get('name'))

                for f_name in all_disk_files:
                    # Check if file belongs to this user (e.g. starts with [Susanti_... or contains user name)
                    is_match = f"[{sanitized_user_prefix}" in f_name or f"[{user_id}" in f_name or f"[{user_name}" in f_name
                    if is_match and f_name not in known_files:
                        f_path = os.path.join(UPLOADS_DIR, f_name)
                        f_size_kb = f"{round(os.path.getsize(f_path) / 1024, 1)} KB"
                        f_url = f"/PKKS%202026/{urllib.parse.quote(f_name)}"
                        new_file_obj = {
                            "id": f"sync_{int(os.path.getmtime(f_path))}_{f_name[:8]}",
                            "name": f_name,
                            "savedName": f_name,
                            "url": f_url,
                            "folder": PKKS_FOLDER_NAME,
                            "user": user_name,
                            "size": f_size_kb
                        }
                        if '1.1' not in data['scores']:
                            data['scores']['1.1'] = {"skor": 0, "uploadedFiles": []}
                        if 'uploadedFiles' not in data['scores']['1.1']:
                            data['scores']['1.1']['uploadedFiles'] = []
                        data['scores']['1.1']['uploadedFiles'].append(new_file_obj)

            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))
            return

        unquoted = urllib.parse.unquote(parsed_url.path)
        if unquoted.startswith('/PKKS 2026/') or unquoted.startswith(f'/{PKKS_FOLDER_NAME}/') or unquoted.startswith('/uploads/'):
            filepath = self.translate_path(self.path)
            if os.path.exists(filepath) and os.path.isfile(filepath):
                self.send_response(200)
                ext = os.path.splitext(filepath)[1].lower()
                mime_types = {
                    '.pdf': 'application/pdf',
                    '.jpg': 'image/jpeg',
                    '.jpeg': 'image/jpeg',
                    '.png': 'image/png',
                    '.gif': 'image/gif',
                    '.webp': 'image/webp',
                    '.svg': 'image/svg+xml',
                    '.txt': 'text/plain',
                    '.html': 'text/html',
                    '.doc': 'application/msword',
                    '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
                }
                content_type = mime_types.get(ext, 'application/octet-stream')
                self.send_header('Content-Type', content_type)

                is_download = 'download' in query
                disposition = 'attachment' if is_download else 'inline'
                self.send_header('Content-Disposition', f'{disposition}; filename="{os.path.basename(filepath)}"')
                self.send_header('Content-Length', str(os.path.getsize(filepath)))
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                try:
                    with open(filepath, 'rb') as f:
                        while True:
                            chunk = f.read(65536)
                            if not chunk:
                                break
                            self.wfile.write(chunk)
                except Exception:
                    pass
                return
            else:
                self.send_response(404)
                self.end_headers()
                return

        return super().do_GET()

    def do_POST(self):
        if self.path == '/api/settings':
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            try:
                new_settings = json.loads(post_data.decode('utf-8'))
                save_settings(new_settings)
                self.send_response(200)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps({"status": "success", "message": "Pengaturan berhasil disimpan!"}).encode('utf-8'))
            except Exception as e:
                self.send_response(500)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps({"status": "error", "message": str(e)}).encode('utf-8'))
            return

        if self.path == '/api/login':
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            try:
                body = json.loads(post_data.decode('utf-8'))
                user_id = body.get('username', '').strip()
                password = body.get('password', '').strip()

                settings = load_settings()
                users = settings.get('users', [])
                default_pwd = settings.get('defaultPassword', 'Sditannisa')

                user_obj = next((u for u in users if u['id'] == user_id or u['name'].lower() == user_id.lower()), None)
                if user_obj and password == default_pwd:
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json; charset=utf-8')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    self.wfile.write(json.dumps({
                        "status": "success",
                        "message": "Login berhasil!",
                        "user": user_obj
                    }).encode('utf-8'))
                else:
                    self.send_response(401)
                    self.send_header('Content-Type', 'application/json; charset=utf-8')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    self.wfile.write(json.dumps({
                        "status": "error",
                        "message": f"Username atau Password salah! (Default Password saat ini: {default_pwd})"
                    }).encode('utf-8'))
            except Exception as e:
                self.send_response(400)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps({"status": "error", "message": str(e)}).encode('utf-8'))
            return

        if self.path == '/api/save':
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            try:
                data = json.loads(post_data.decode('utf-8'))
                user_id = data.get('user', 'abdul_yakub')
                user_file = os.path.join(DATA_DIR, f"data_{user_id}.json")
                with open(user_file, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)

                self.send_response(200)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps({"status": "success", "message": "Data berhasil disimpan!"}).encode('utf-8'))
            except Exception as e:
                self.send_response(500)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps({"status": "error", "message": str(e)}).encode('utf-8'))
            return

        if self.path == '/api/delete-file':
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            try:
                body = json.loads(post_data.decode('utf-8'))
                file_name = body.get('filename', '').strip()
                user_id = body.get('user', '').strip()

                if file_name:
                    safe_name = os.path.basename(file_name)
                    file_path = os.path.join(UPLOADS_DIR, safe_name)
                    if os.path.exists(file_path) and os.path.isfile(file_path):
                        try:
                            os.remove(file_path)
                            print(f"Successfully deleted physical file: {file_path}")
                        except Exception as e:
                            print(f"Error removing physical file {safe_name}: {e}")

                    if user_id:
                        user_file = os.path.join(DATA_DIR, f"data_{user_id}.json")
                        if os.path.exists(user_file):
                            try:
                                with open(user_file, 'r', encoding='utf-8') as f:
                                    udata = json.load(f)
                                if 'scores' in udata:
                                    for item_id, item_val in udata['scores'].items():
                                        if isinstance(item_val, dict) and 'uploadedFiles' in item_val:
                                            item_val['uploadedFiles'] = [
                                                uf for uf in item_val['uploadedFiles']
                                                if uf.get('savedName') != safe_name and uf.get('name') != safe_name
                                            ]
                                with open(user_file, 'w', encoding='utf-8') as f:
                                    json.dump(udata, f, ensure_ascii=False, indent=2)
                            except Exception as e:
                                print(f"Error updating user JSON on delete: {e}")

                self.send_response(200)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps({"status": "success", "message": "File berhasil dihapus secara permanen!"}).encode('utf-8'))
            except Exception as e:
                self.send_response(500)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps({"status": "error", "message": str(e)}).encode('utf-8'))
            return

        if self.path == '/api/upload':
            content_type = self.headers.get('Content-Type', '')
            if 'boundary=' not in content_type:
                self.send_response(400)
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(b'{"status":"error","message":"Invalid Content-Type"}')
                return
            
            boundary_str = content_type.split('boundary=')[1].split(';')[0].strip()
            boundary = ('' if boundary_str.startswith('--') else '--') + boundary_str
            boundary_bytes = boundary.encode('utf-8')

            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length)

            parts = body.split(boundary_bytes)
            uploaded_files = []

            user_name_prefix = "Umum"
            for part in parts:
                if b'name="username"' in part:
                    header_end = part.find(b'\r\n\r\n')
                    if header_end != -1:
                        val = part[header_end+4:].decode('utf-8', errors='ignore').strip()
                        if val:
                            user_name_prefix = val

            for part in parts:
                if b'filename="' in part:
                    header_end = part.find(b'\r\n\r\n')
                    if header_end != -1:
                        headers_text = part[:header_end].decode('utf-8', errors='ignore')
                        content = part[header_end+4:]
                        if content.endswith(b'\r\n'):
                            content = content[:-2]
                        if content.endswith(b'--'):
                            content = content[:-2]

                        m = re.search(r'filename="([^"]+)"', headers_text)
                        if m:
                            orig_filename = os.path.basename(m.group(1))
                            sanitized_file = "".join([c for c in orig_filename if c.isalnum() or c in "._- "])
                            sanitized_user = "".join([c for c in user_name_prefix if c.isalnum() or c in "_- "]).replace(" ", "_")
                            if not sanitized_file:
                                sanitized_file = "file_upload.bin"
                            
                            import time
                            unique_name = f"[{sanitized_user}]_{int(time.time())}_{sanitized_file}"
                            save_path = os.path.join(UPLOADS_DIR, unique_name)

                            with open(save_path, 'wb') as f:
                                f.write(content)
                                f.flush()
                                os.fsync(f.fileno())

                            file_url = f"/PKKS%202026/{urllib.parse.quote(unique_name)}"
                            gdrive_folder_link = load_settings().get('googleDriveLink', '')
                            gdrive_direct_url = upload_file_to_gdrive_api(save_path, orig_filename, user_name_prefix, gdrive_folder_link)

                            uploaded_files.append({
                                "originalName": orig_filename,
                                "savedName": unique_name,
                                "url": gdrive_direct_url or (gdrive_folder_link if gdrive_folder_link else file_url),
                                "isDrive": bool(gdrive_direct_url or gdrive_folder_link),
                                "folder": "Google Drive" if gdrive_folder_link else PKKS_FOLDER_NAME,
                                "user": user_name_prefix,
                                "size": len(content)
                            })

            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({
                "status": "success",
                "message": f"File berhasil disimpan ke folder {PKKS_FOLDER_NAME}!",
                "files": uploaded_files
            }).encode('utf-8'))
            return

        self.send_response(404)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

if __name__ == '__main__':
    os.chdir(BASE_DIR)
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("", PORT), PKKSRequestHandler) as httpd:
        print("\n" + "="*65)
        print("SISTEM MULTI-USER PKKS SDIT AN-NISA WEB SERVER")
        print(f"Folder Berkas: PKKS 2026 ({UPLOADS_DIR})")
        print(f"Jumlah Akun Guru/Kepsek: {len(load_settings().get('users', []))}")
        print("="*65)
        print(f"Status: Server Aktif & Berjalan!")
        print(f"URL Browser Direct: http://localhost:{PORT}")
        print("="*65 + "\n")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nServer dihentikan.")
