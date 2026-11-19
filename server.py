# -*- coding: utf-8 -*-
import http.server
import socketserver
import json
import os
import re

PORT = 5500
DIRECTORY = os.path.dirname(os.path.abspath(__file__))

def update_html_files(mapping):
    """
    mapping is dict: { "IMG_0413.JPG": "vu-dinh-viet", ... }
    Updates CUTE_TEACHERS in index.html and Lưu bút mái tường.html
    """
    teacher_to_photo = {}
    for filename, teacher_id in mapping.items():
        if teacher_id and not teacher_id.startswith("__"):
            teacher_to_photo[teacher_id] = "teachers_photos/" + filename

    target_files = ["index.html", "Lưu bút mái tường.html"]
    updated_files = []

    for fn in target_files:
        path = os.path.join(DIRECTORY, fn)
        if not os.path.exists(path):
            continue
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()

            s_marker = "const CUTE_TEACHERS = "
            e_marker = "];\n\n        // Tinh so hoa ca nhan"
            s_idx = content.find(s_marker)
            e_idx = content.find(e_marker)

            if s_idx != -1 and e_idx != -1:
                json_str = content[s_idx + len(s_marker) : e_idx + 1].strip()
                teachers = json.loads(json_str)

                for t in teachers:
                    tid = t.get("id")
                    if tid in teacher_to_photo:
                        t["avatarImg"] = teacher_to_photo[tid]
                    elif "avatarImg" in t and tid not in teacher_to_photo:
                        del t["avatarImg"]

                new_json_str = json.dumps(teachers, ensure_ascii=False, indent=12)
                content = content[:s_idx + len(s_marker)] + new_json_str + content[e_idx + 1:]

                with open(path, "w", encoding="utf-8") as f:
                    f.write(content)
                updated_files.append(fn)
        except Exception as e:
            print(f"Error updating {fn}: {e}")

    return updated_files

class CustomHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

    def do_GET(self):
        if self.path == "/api/get-mapping":
            mapping_file = os.path.join(DIRECTORY, "teachers_mapping.json")
            data = {}
            if os.path.exists(mapping_file):
                try:
                    with open(mapping_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                except Exception as e:
                    print("Error reading mapping:", e)
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))
            return

        super().do_GET()

    def do_POST(self):
        if self.path == "/api/save-mapping":
            try:
                content_len = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(content_len)
                payload = json.loads(body.decode("utf-8"))
                mapping = payload.get("mapping", payload)

                # Save to teachers_mapping.json
                mapping_path = os.path.join(DIRECTORY, "teachers_mapping.json")
                with open(mapping_path, "w", encoding="utf-8") as f:
                    json.dump(mapping, f, ensure_ascii=False, indent=2)

                # Update HTML files directly
                updated_files = update_html_files(mapping)

                valid_count = len([v for v in mapping.values() if v and not v.startswith("__")])
                response = {
                    "success": True,
                    "count": valid_count,
                    "updatedFiles": updated_files,
                    "message": f"Đã lưu thành công {valid_count} ảnh Thầy Cô vào mã nguồn web!"
                }
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.end_headers()
                self.wfile.write(json.dumps(response, ensure_ascii=False).encode("utf-8"))
                print(f"[API] Saved mapping: {valid_count} assigned teachers. Updated: {updated_files}")
            except Exception as e:
                print(f"[API] Error saving mapping: {e}")
                self.send_response(500)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.end_headers()
                self.wfile.write(json.dumps({"success": False, "error": str(e)}).encode("utf-8"))
            return

        self.send_response(404)
        self.end_headers()

if __name__ == "__main__":
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("", PORT), CustomHandler) as httpd:
        print(f"Server started at http://localhost:{PORT}")
        httpd.serve_forever()
