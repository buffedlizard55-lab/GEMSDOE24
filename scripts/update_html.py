import json
import re

with open("evidence/myhgb_run_card_20261025.json") as f:
    card = json.loads(f.read())
filename = card["submission_name"]


def replace_in_file(path):
    with open(path, "r") as f:
        content = f.read()
    content = re.sub(r'gems24-myhgb-[^"]+\.tif', filename, content)
    with open(path, "w") as f:
        f.write(content)


replace_in_file("docs/executive-summary.html")
replace_in_file("docs/index.html")
print(f"Updated HTML files with {filename}")
