import tkinter as tk
from tkinter import messagebox
from tkinter import filedialog
import csv
import requests
import re
from bs4 import BeautifulSoup
import multiprocessing
from multiprocessing import Pool

# متغير لتتبع عدد مرات حفظ النتائج
output_count = 0

def extract_emails_from_text(text):
    pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    emails = re.findall(pattern, text)
    return list(set(emails))

def sanitize_email(email):
    domain = email.split('@')[-1]
    if domain[0].isupper():
        return email
    else:
        for i, char in enumerate(domain):
            if char.isupper():
                domain = domain[:i]
                break
        return email.split('@')[0] + '@' + domain

def extract_emails_from_html(html):
    soup = BeautifulSoup(html, 'html.parser')
    text = soup.get_text()
    return extract_emails_from_text(text)

def is_valid_domain(domain):
    return not re.match(r'^\d{1,3}(\.\d{1,3}){3}$', domain)

def get_internal_links(url):
    try:
        response = requests.get(url)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            links = set()
            for a in soup.find_all('a', href=True):
                href = a['href']
                if href.startswith('/') or '/policies/' in href:
                    links.add(requests.compat.urljoin(url, href))
            return links
    except requests.exceptions.RequestException as e:
        print('❌', url, ':', e)
    return set()

def scrape_emails_from_domain(domain):
    base_url = 'http://' + domain
    emails = []
    try:
        response = requests.get(base_url)
        if response.status_code == 200:
            extracted_emails = extract_emails_from_html(response.text)
            extracted_emails = [sanitize_email(email) for email in extracted_emails]
            emails.extend(extracted_emails)

            internal_links = get_internal_links(base_url)
            for url in internal_links:
                response = requests.get(url)
                if response.status_code == 200:
                    extracted_emails = extract_emails_from_html(response.text)
                    extracted_emails = [sanitize_email(email) for email in extracted_emails]
                    emails.extend(extracted_emails)

            return domain, list(set(emails))
    except requests.exceptions.RequestException as e:
        print('❌', domain, ':', e)
    return domain, None

def scrape_emails_from_domains(domains):
    global output_count  # استخدام المتغير العالمي
    pool = Pool(processes=multiprocessing.cpu_count())
    results = pool.map(scrape_emails_from_domain, domains)
    pool.close()
    pool.join()

    email_dict = {}
    for domain, emails in results:
        if emails:
            email_dict[domain] = emails

    table_data = []
    for domain in domains:
        if is_valid_domain(domain):
            emails = email_dict.get(domain, [])
            table_data.append([domain] + emails)

    # حفظ الجدول في ملف CSV باسم فريد
    output_count += 1  # زيادة العداد
    output_filename = f'output_{output_count}.csv'  # إنشاء اسم جديد
    with open(output_filename, 'w', newline='') as file:
        writer = csv.writer(file)
        headers = ['Domain'] + [f'Email {i + 1}' for i in range(max(len(emails) for emails in table_data) - 1)]
        writer.writerow(headers)
        writer.writerows(table_data)

    print(f'Output saved to {output_filename}')

# إنشاء نافذة المستخدم باستخدام Tkinter
window = tk.Tk()
window.title("User Interface")
window.geometry("400x300")

def paste_text():
    try:
        text = window.clipboard_get()
        text_entry.delete(1.0, tk.END)
        text_entry.insert(tk.END, text)
    except Exception:
        messagebox.showerror("Error", "Unable to paste text.")

def import_text_file():
    try:
        file_path = filedialog.askopenfilename(filetypes=[("Text files", "*.txt")])
        with open(file_path, 'r') as file:
            text = file.read()
        text_entry.delete(1.0, tk.END)
        text_entry.insert(tk.END, text)
    except FileNotFoundError:
        messagebox.showerror("Error", "File not found.")

def extract_emails():
    random_text = text_entry.get("1.0", "end-1c")
    pattern = r'\b(?:https?://)?(?:www\.)?([^\s/?\.]+(?:\.[^\s/?\.]+)+)\b'
    domains = re.findall(pattern, random_text)

    unique_domains = []
    for domain in domains:
        if is_valid_domain(domain) and domain not in unique_domains:
            unique_domains.append(domain)

    scrape_emails_from_domains(unique_domains)

paste_button = tk.Button(window, text="Paste", command=paste_text)
paste_button.pack()

import_text_button = tk.Button(window, text="Import txt file", command=import_text_file)
import_text_button.pack()

text_entry = tk.Text(window, height=10, width=50)
text_entry.pack()

extract_button = tk.Button(window, text="Start", command=extract_emails)
extract_button.pack()

window.mainloop()
