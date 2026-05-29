import os

mappings = {
    "quarky_ai.memory": "MAIINNN.Memory",
    "quarky_ai.infrastructure": "AppStudio.Infrastructure",
    "quarky_ai.action": "MAIINNN.Functions.action",
    "quarky_ai.automation": "MAIINNN.Functions.automation",
    "quarky_ai.habits": "MAIINNN.Functions.habits",
    "quarky_ai.integrations": "MAIINNN.Functions.integrations",
    "quarky_ai.monitor": "MAIINNN.Functions.monitor",
    "quarky_ai.web": "MAIINNN.Functions.web",
    "quarky_ai.session": "MAIINNN.session",
    "quarky_ai.cli": "MAIINNN.cli",
    "quarky_ai.api": "AppStudio.API",
    "quarky_ai.start": "AppStudio.Start",
    "quarky_ai.gui": "AppStudio.GUI",
    "quarky_ai.voice": "AppStudio.Voice",
    "quarky_ai.nlp": "MAIINNN.NLP",
    "quarky_ai.intelligence": "MAIINNN.Intelligence",
    "quarky_ai.learning": "MAIINNN.Learning",
    "quarky_ai.decision": "MAIINNN.Decision",
    "quarky_ai.orchestrator": "MAIINNN.Orchestrator",
    "quarky_ai.config": "AppStudio.Config",
    "quarky_ai.learner": "MAIINNN.learner",
    "quarky_ai.backup": "AppStudio.backup",
    "quarky_ai.config_watcher": "AppStudio.config_watcher",
    "quarky_ai.updater": "AppStudio.updater",
    "MAIINNN.Functions.action.registry": "MAIINNN.Functions.action.registry",
    "MAIINNN.Functions.action.app_discovery": "MAIINNN.Functions.action.app_discovery",
    "MAIINNN.Functions.action.app_launcher": "MAIINNN.Functions.action.app_launcher",
}

def fix_file(path):
    if "fix_imports.py" in path: return False
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    new_content = content
    for old, new in mappings.items():
        new_content = new_content.replace(old, new)
    if new_content != content:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        return True
    return False

for root, dirs, files in os.walk("."):
    if any(p in root for p in [".git", "__pycache__", "Migration", "Data"]):
        continue
    for file in files:
        if file.endswith(".py"):
            fix_file(os.path.join(root, file))
