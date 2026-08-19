path = r"c:\Users\FERNANDO PARRA\Desktop\PROYECT\BLACKERP\app\ui\login_window.py"
with open(path, "r", encoding="utf-8") as f:
    lines = f.readlines()

# Remove extra blank lines (index 279 and 280)
del lines[279]
del lines[279]

with open(path, "w", encoding="utf-8") as f:
    f.writelines(lines)

print("Done - file cleaned")
