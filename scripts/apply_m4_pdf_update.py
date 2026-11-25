import os
import shutil
import time

orig = r"D:\Infosys springboards\docs\Milestone4_Documentation.pdf"
fixed = r"D:\Infosys springboards\docs\Milestone4_Documentation_fixed.pdf"

if not os.path.exists(fixed):
    print("Fixed PDF not found!")
    exit(1)

for attempt in range(5):
    try:
        shutil.copyfile(fixed, orig)
        print("SUCCESS: Milestone4_Documentation.pdf has been replaced with the clean version!")
        break
    except PermissionError:
        time.sleep(1)
else:
    print("Milestone4_Documentation.pdf is still currently open in a PDF viewer.")
