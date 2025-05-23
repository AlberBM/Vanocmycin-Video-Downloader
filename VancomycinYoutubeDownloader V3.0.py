import os
import re
import urllib.parse
from yt_dlp import YoutubeDL
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from threading import Thread, Lock
from youtubesearchpython import VideosSearch

# --- Globals for batch download tracking ---
download_results = []
download_lock = Lock()
total_downloads = 0
completed_downloads = 0

# --- Functions ---

def browse_download_location():
    folder = filedialog.askdirectory()
    if folder:
        download_path.set(folder)

def download_youtube_videos():
    global total_downloads, completed_downloads, download_results
    raw_input = url_text.get("1.0", tk.END).strip().splitlines()
    encoded_urls = [urllib.parse.quote(url.strip(), safe=':/?=&') for url in raw_input if url.strip()]

    valid_urls = [urllib.parse.unquote(url) for url in encoded_urls if url.strip()]

    selected_quality = quality_combobox.get()
    output_folder = download_path.get()

    if not valid_urls:
        messagebox.showerror("Error", "Please enter at least one valid YouTube URL.")
        return

    if not selected_quality:
        messagebox.showerror("Error", "Please select a quality.")
        return

    if not output_folder.strip():
        messagebox.showerror("Error", "Please select a download location.")
        return

    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    # Reset tracking variables before starting downloads
    with download_lock:
        download_results.clear()
        total_downloads = len(valid_urls)
        completed_downloads = 0

    quality_mapping = {
        "Original (Best Quality)": "bestvideo+bestaudio/best",
        "Lower Quality": "bestvideo[height<=480]+bestaudio/best",
        "Lowest Quality": "worst",
        "Audio Only (MP3)": "bestaudio"
    }

    for url in valid_urls:
        ydl_opts = {
            'outtmpl': os.path.join(output_folder, "%(title)s.%(ext)s"),
            'format': quality_mapping[selected_quality],
            'progress_hooks': [progress_hook],
            'noplaylist': True
        }

        if "Audio Only (MP3)" in selected_quality:
            ydl_opts['postprocessors'] = [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '128',
            }]
        else:
            ydl_opts['merge_output_format'] = 'mp4'

        # Run each download in its own thread
        Thread(target=run_download, args=(ydl_opts, urllib.parse.unquote(url)), daemon=True).start()

def run_download(ydl_opts, video_url):
    global completed_downloads
    try:
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=True)
            title = info.get('title', 'Unknown title')
        status = "Success"
    except Exception as e:
        title = "Unknown title"
        status = f"Failed: {str(e)}"

    # Append result thread-safely
    with download_lock:
        download_results.append((title, video_url, status))
        completed_downloads += 1

        # When all downloads finish, show summary
        if completed_downloads == total_downloads:
            root.after(0, show_download_summary)

def show_download_summary():
    summary_window = tk.Toplevel(root)
    summary_window.title("Download Summary")
    summary_window.geometry("600x400")
    summary_window.configure(bg="#1F1F1F")

    label = ttk.Label(summary_window, text="Download Summary", font=("Segoe UI Black", 14, "bold"), background="#1F1F1F", foreground="#4CAF50")
    label.pack(pady=10)

    summary_text = tk.Text(summary_window, bg="#2B2B2B", fg="white", font=("Segoe UI", 10), state='normal')
    summary_text.pack(expand=True, fill='both', padx=10, pady=10)

    for title, url, status in download_results:
        summary_text.insert(tk.END, f"Title: {title}\nURL: {url}\nStatus: {status}\n\n")

    summary_text.config(state='disabled')

    close_btn = ttk.Button(summary_window, text="Close", command=summary_window.destroy)
    close_btn.pack(pady=10)

def progress_hook(status):
    if status['status'] == 'downloading':
        total_bytes = status.get('total_bytes') or status.get('total_bytes_estimate')
        downloaded_bytes = status.get('downloaded_bytes', 0)
        speed = status.get('speed', 0)
        eta = status.get('eta', 0)

        if total_bytes:
            percentage = (downloaded_bytes / total_bytes) * 100
            progress_bar['value'] = percentage
            progress_label.config(text=f"Progress: {percentage:.2f}%")
        else:
            progress_label.config(text="Progress: Calculating...")

        speed_mb = speed / 1024 / 1024 if speed else 0
        speed_label.config(text=f"Speed: {speed_mb:.2f} MB/s")

        total_size_mb = total_bytes / 1024 / 1024 if total_bytes else 0
        total_size_label.config(text=f"Total Size: {total_size_mb:.2f} MB")

        eta_label.config(text=f"ETA: {eta} seconds" if eta else "ETA: Calculating...")

    elif status['status'] == 'finished':
        progress_bar['value'] = 100
        progress_label.config(text="Download Complete")
        speed_label.config(text="Speed: 0 MB/s")
        eta_label.config(text="ETA: Completed")

def toggle_search():
    if search_enabled.get():
        search_frame.grid()
    else:
        search_frame.grid_remove()

def start_youtube_search():
    query = search_entry.get().strip()
    if not query:
        messagebox.showwarning("Warning", "Enter a search query.")
        return
    Thread(target=search_youtube_thread, args=(query,), daemon=True).start()

def search_youtube_thread(query):
    try:
        search = VideosSearch(query, limit=10)
        results = search.result()['result']
        # Sort descending by views
        videos = sorted(results, key=lambda v: int(v['viewCount']['text'].replace(',', '').replace(' views', '')), reverse=True)
        urls = []
        for v in videos:
            duration = v.get('duration', 'N/A')
            title = v['title']
            views = v['viewCount']['text']
            urls.append((f"{title} [{duration}] ({views})", v['link']))

        def update_ui():
            results_listbox.delete(0, tk.END)
            search_youtube_thread.result_urls = []
            for title, url in urls:
                results_listbox.insert(tk.END, title)
                search_youtube_thread.result_urls.append(url)

        root.after(0, update_ui)

    except Exception as e:
        messagebox.showerror("Error", f"Search failed: {str(e)}")

# --- GUI Setup ---

root = tk.Tk()
root.title("Vancomycin Video Downloader")
root.geometry("760x700")
root.configure(bg="#1F1F1F")

style = ttk.Style()
style.theme_use('clam')
style.configure("TLabel", font=("Segoe UI", 10), background="#1F1F1F", foreground="white")
style.configure("TEntry", font=("Segoe UI", 10))
style.configure("TCombobox", font=("Segoe UI", 10))
style.configure("TButton", font=("Segoe UI", 10), background="#4CAF50", foreground="white")
style.configure("TProgressbar", thickness=15)

title_label = tk.Label(root, text="Vancomycin Video Downloader", font=("Segoe UI Black", 16, "bold"), fg="#4CAF50", bg="#1F1F1F")
title_label.grid(row=0, column=0, columnspan=3, pady=15)

url_label = ttk.Label(root, text="YouTube URLs (one per line):")
url_label.grid(row=1, column=0, padx=10, pady=10, sticky="ne")

url_text = tk.Text(root, height=7, width=60, font=("Segoe UI", 10), undo=True, autoseparators=True, maxundo=-1, bg="#2B2B2B", fg="white", insertbackground="white")
url_text.grid(row=1, column=1, padx=10, pady=10)
url_text.bind("<Control-z>", lambda event: url_text.edit_undo())
url_text.bind("<Control-Z>", lambda event: url_text.edit_redo())

quality_label = ttk.Label(root, text="Select Quality:")
quality_label.grid(row=2, column=0, padx=10, pady=10, sticky="e")
quality_combobox = ttk.Combobox(root, values=["Original (Best Quality)", "Lower Quality", "Lowest Quality", "Audio Only (MP3)"], state="readonly", width=40)
quality_combobox.set("Original (Best Quality)")
quality_combobox.grid(row=2, column=1, padx=10, pady=10)

download_label = ttk.Label(root, text="Download Location:")
download_label.grid(row=3, column=0, padx=10, pady=10, sticky="e")
download_path = tk.StringVar()
download_entry = ttk.Entry(root, textvariable=download_path, width=45)
download_entry.grid(row=3, column=1, padx=10, pady=10)
browse_button = ttk.Button(root, text="Browse", command=browse_download_location)
browse_button.grid(row=3, column=2, padx=10, pady=10)

progress_bar = ttk.Progressbar(root, length=500, mode="determinate")
progress_bar.grid(row=4, column=0, columnspan=3, pady=20)
progress_label = ttk.Label(root, text="Progress: 0.00%")
progress_label.grid(row=5, column=0, columnspan=3, pady=5)
speed_label = ttk.Label(root, text="Speed: 0.00 MB/s")
speed_label.grid(row=6, column=0, columnspan=3, pady=5)
total_size_label = ttk.Label(root, text="Total Size: 0.00 MB")
total_size_label.grid(row=7, column=0, columnspan=3, pady=5)
eta_label = ttk.Label(root, text="ETA: Calculating...")
eta_label.grid(row=8, column=0, columnspan=3, pady=5)

download_button = ttk.Button(root, text="Download", command=download_youtube_videos)
download_button.grid(row=9, column=0, columnspan=3, pady=20)

# --- YouTube Search Option ---
search_enabled = tk.BooleanVar()
search_checkbox = ttk.Checkbutton(root, text="Enable YouTube Search", variable=search_enabled, command=toggle_search)
search_checkbox.grid(row=10, column=0, columnspan=3, pady=10)

search_frame = tk.Frame(root, bg="#1F1F1F")
search_frame.grid(row=11, column=0, columnspan=3, pady=5)
search_frame.grid_remove()

search_label = ttk.Label(search_frame, text="Search YouTube:")
search_label.grid(row=0, column=0, padx=5)

search_entry = ttk.Entry(search_frame, width=40)
search_entry.grid(row=0, column=1, padx=5)

# Bind Enter key on search entry to start search
search_entry.bind("<Return>", lambda event: start_youtube_search())

search_button = ttk.Button(search_frame, text="Search", command=start_youtube_search)
search_button.grid(row=0, column=2, padx=5)

results_listbox = tk.Listbox(search_frame, bg="#2B2B2B", fg="white", width=80, height=8)
results_listbox.grid(row=1, column=0, columnspan=3, pady=10)

def insert_selected_url(event):
    try:
        index = results_listbox.curselection()[0]
        url = search_youtube_thread.result_urls[index]
        current_text = url_text.get("1.0", tk.END).strip()
        # Append selected URL if not already in list
        if url not in current_text:
            url_text.insert(tk.END, url + "\n")
    except IndexError:
        pass

results_listbox.bind("<Double-1>", insert_selected_url)

root.mainloop()
