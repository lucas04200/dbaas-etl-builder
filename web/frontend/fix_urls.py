import glob

vue_files = glob.glob('src/components/**/*.vue', recursive=True)
for file_path in vue_files:
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    original = content
    content = content.replace("`http://localhost:${", "`http://${hostname}:${")
    content = content.replace("`redis://localhost:${", "`redis://${hostname}:${")
    content = content.replace("http://localhost:{{", "http://{{ hostname }}:{{")
    content = content.replace("redis://localhost:{{", "redis://{{ hostname }}:{{")
    content = content.replace("mysql://root:<pass>@localhost:{{", "mysql://root:<pass>@{{ hostname }}:{{")
    content = content.replace("curl http://localhost:{{", "curl http://{{ hostname }}:{{")
    content = content.replace('base_url="http://localhost:{{', 'base_url="http://{{ hostname }}:{{')
    content = content.replace("localhost:port", "IP:port")
    content = content.replace("localhost:{{", "{{ hostname }}:{{")

    if content != original:
        if "const hostname" not in content and "hostname" in content:
            content = content.replace("<script setup>", "<script setup>\nconst hostname = window.location.hostname;")
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
print("done")
