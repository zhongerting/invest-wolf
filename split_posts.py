import re
import os
from datetime import datetime, timedelta
from collections import defaultdict

input_file = r"e:\杂项\NGA狼\nga_master_posts.md"
output_dir = r"e:\杂项\NGA狼"

with open(input_file, "r", encoding="utf-8") as f:
    content = f.read()

post_pattern = re.compile(r'^(##### <span id="pid\d+">\d+\.\[\d+\] \\<pid:\d+\\> (\d{4}-\d{2}-\d{2}) \d{2}:\d{2}:\d{2} by .+?</span>)$', re.MULTILINE)

header_end = 0
header_match = re.search(r'^----$', content, re.MULTILINE)
if header_match:
    header_end = header_match.end()

matches = list(re.finditer(r'^##### <span id="pid\d+">', content, re.MULTILINE))

posts = []
for i, match in enumerate(matches):
    start = match.start()
    if i + 1 < len(matches):
        end = matches[i + 1].start()
    else:
        end = len(content)
    post_content = content[start:end]
    date_match = re.search(r'(\d{4}-\d{2}-\d{2}) \d{2}:\d{2}:\d{2}', post_content)
    if date_match:
        date_str = date_match.group(1)
        date = datetime.strptime(date_str, "%Y-%m-%d")
        posts.append((date, start, end))

if not posts:
    print("No posts found!")
    exit(1)

print(f"Found {len(posts)} posts")
print(f"First post date: {posts[0][0].strftime('%Y-%m-%d')}")
print(f"Last post date: {posts[-1][0].strftime('%Y-%m-%d')}")

first_date = posts[0][0]
last_date = posts[-1][0]

current_start = datetime(first_date.year, first_date.month, 1)
if first_date.day > 15:
    current_start = datetime(first_date.year, first_date.month, 16)
else:
    current_start = datetime(first_date.year, first_date.month, 1)

if last_date.day <= 15:
    current_end = datetime(last_date.year, last_date.month, 15)
else:
    current_end = datetime(last_date.year, last_date.month, 1) + timedelta(days=32)
    current_end = current_end.replace(day=1) - timedelta(days=1)

half_months = []
cursor = current_start
while cursor <= last_date:
    if cursor.day == 1:
        period_end = datetime(cursor.year, cursor.month, 15)
    else:
        next_month = cursor.replace(day=28) + timedelta(days=4)
        period_end = next_month - timedelta(days=next_month.day)
    if period_end > last_date:
        period_end = last_date
    half_months.append((cursor, period_end))
    if cursor.day == 1:
        cursor = datetime(cursor.year, cursor.month, 16)
    else:
        cursor = (cursor.replace(day=28) + timedelta(days=4)).replace(day=1)

buckets = defaultdict(list)
for date, start, end in posts:
    for period_start, period_end in half_months:
        if period_start <= date <= period_end:
            buckets[(period_start, period_end)].append((date, start, end))
            break

header = content[:header_end] + "\n\n"

for period_start, period_end in half_months:
    period_posts = buckets.get((period_start, period_end), [])
    if not period_posts:
        continue

    filename = f"{period_start.strftime('%Y%m%d')}-{period_end.strftime('%Y%m%d')}_nga_master_posts.md"
    filepath = os.path.join(output_dir, filename)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(header)
        for _, start, end in period_posts:
            f.write(content[start:end])

    print(f"Created {filename} with {len(period_posts)} posts")

print("\nDone!")