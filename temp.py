import os


def print_tree(root_path, skip_dirs={"venv"}):
    for root, dirs, files in os.walk(root_path):
        # modify dirs in-place to prevent walking into them
        dirs[:] = [d for d in dirs if d not in skip_dirs]

        level = root.replace(root_path, "").count(os.sep)
        indent = "    " * level
        print(f"{indent}{os.path.basename(root)}/")

        sub_indent = "    " * (level + 1)
        for f in files:
            print(f"{sub_indent}{f}")


print_tree(r"D:\shoe_inventory")
